-- Request logs rules: parse the rules file and match requests against it. See spec/request-logs.md
-- d2_docker/request_logs.py validates the same structure; shared cases: test/request-logs

local cjson = require "cjson.safe"

local _M = {}

local DEFAULTS = { maxAgeDays = 7, maxBodyBytes = 1024 * 1024 }
local FIELDS = { method = true, url = true, status = true }
local OPERATORS = { equal = true, notEqual = true, match = true, notMatch = true }
local OPERATORS_LIST = "equal, match, notEqual, notMatch"

-- Separate decoder that tags arrays, so [] and {} can be told apart
local json = cjson.new()
json.decode_array_with_array_mt(true)

local function is_array(value)
    return type(value) == "table" and getmetatable(value) == cjson.array_mt
end

local function is_object(value)
    return type(value) == "table" and not is_array(value)
end

local function is_positive_integer(value)
    return type(value) == "number" and value > 0 and value == math.floor(value)
end

-- Operands are strings. Status also accepts integers (i.e. 404)
local function normalize_operand(field, value)
    if type(value) == "string" then
        return value
    elseif field == "status" and type(value) == "number" and value == math.floor(value) then
        return tostring(value)
    end
end

-- Errors are raised with level 0: the message is for the user, without a Lua source position
local function fail(message, ...)
    error(string.format(message, ...), 0)
end

local function parse_condition(field, value)
    if not FIELDS[field] then fail("unknown field: %s", field) end

    local operand = normalize_operand(field, value)
    if operand then
        return { field = field, operator = "equal", value = operand }
    end

    local operator
    if is_object(value) then
        operator, operand = next(value)
        operand = normalize_operand(field, operand)
    end

    if not OPERATORS[operator] or next(value, operator) or not operand then
        fail("field %s: expected a string or an object with one operator (%s)", field, OPERATORS_LIST)
    end

    if operator == "match" or operator == "notMatch" then
        local _, _, err = ngx.re.find("", operand, "jo")
        if err then fail("field %s: invalid regex %s: %s", field, operand, err) end
    end

    return { field = field, operator = operator, value = operand }
end

local function parse_rule(rule)
    if not is_object(rule) then fail("rules must be a list of objects") end

    local conditions = {}
    for field, value in pairs(rule) do
        if field ~= "comment" then
            table.insert(conditions, parse_condition(field, value))
        end
    end
    return conditions
end

-- Parse and validate the rules file text. Raise an error with a user message if invalid.
function _M.parse(text)
    local data, err = json.decode(text)
    if data == nil then fail("invalid JSON: %s", err) end
    if not is_object(data) then fail("expected an object") end

    local unknown_keys = {}
    for key in pairs(data) do
        if not (DEFAULTS[key] or key == "rules" or key == "comment") then
            table.insert(unknown_keys, key)
        end
    end
    if #unknown_keys > 0 then
        table.sort(unknown_keys)
        fail("unknown keys: %s", table.concat(unknown_keys, ", "))
    end

    for key in pairs(DEFAULTS) do
        if data[key] ~= nil and not is_positive_integer(data[key]) then
            fail("%s must be a positive integer", key)
        end
    end

    if data.rules ~= nil and not is_array(data.rules) then fail("rules must be a list of objects") end

    local rules = {}
    for _, rule in ipairs(data.rules or {}) do
        table.insert(rules, parse_rule(rule))
    end

    return {
        maxAgeDays = data.maxAgeDays or DEFAULTS.maxAgeDays,
        maxBodyBytes = data.maxBodyBytes or DEFAULTS.maxBodyBytes,
        rules = rules,
    }
end

local function condition_matches(condition, values)
    local actual = values[condition.field]
    -- Not known yet (status in the access phase): don't discard the rule
    if actual == nil then return true end

    local operator = condition.operator
    if operator == "equal" then
        return actual == condition.value
    elseif operator == "notEqual" then
        return actual ~= condition.value
    end

    local matched = ngx.re.find(actual, condition.value, "jo") ~= nil
    return (operator == "match") == matched
end

local function rule_matches(rule, values)
    for _, condition in ipairs(rule) do
        if not condition_matches(condition, values) then return false end
    end
    return true
end

-- Rules are combined with OR, the conditions of a rule with AND
function _M.match(rules, values)
    for _, rule in ipairs(rules) do
        if rule_matches(rule, values) then return true end
    end
    return false
end

return _M
