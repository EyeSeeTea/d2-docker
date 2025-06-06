local cjson = require "cjson.safe"

-- Helpers

-- Example of filters (list of OR groups, each group is a list of AND conditions)

--[[
local default_filters = {{{
    field = "status",
    operator = "match",
    value = "2.."
}, {
    field = "method",
    operator = "equal",
    value = "GET"
}, {
    field = "url",
    operator = "no_match",
    value = "/api/users/"
}}}

--]]

-- Retrieves the actual value based on the field name
local function get_actual_value(field)
    if field == "status" then
        return tostring(ngx.status or 0)
    elseif field == "method" then
        return ngx.req and ngx.req.get_method and ngx.req.get_method() or ""
    elseif field == "url" then
        return ngx.var.request_uri or ""
    else
        ngx.log(ngx.ERR, "Unsupported field: ", field)
        return ""
    end
end

local function parse_condition(condition_str)
    local operator_map = {
        ["=="] = "equal",
        ["!="] = "no_equal",
        ["=~"] = "match",
        ["!~"] = "no_match"
    }

    -- Try each operator in longest-first order
    for op_pattern, op_name in pairs(operator_map) do
        local pattern = "^(.-)" .. op_pattern:gsub("([%p])", "%%%1") .. "(.+)$"
        local field, value = string.match(condition_str, pattern)
        if field and value then
            return {
                field = field,
                operator = op_name,
                value = value
            }
        end
    end

    ngx.log(ngx.ERR, "Failed to parse condition: ", condition_str)
    return nil
end

local function parse_filter_group(filter_str)
    local group = {}

    for condition_str in string.gmatch(filter_str, "[^+]+") do
        local condition = parse_condition(condition_str)
        if condition then
            table.insert(group, condition)
        end
    end

    return group
end

local function parse_filter_groups(filter_str)
    local filters = {}

    for group_str in string.gmatch(filter_str, "[^,]+") do
        local group = parse_filter_group(group_str)
        table.insert(filters, group)
    end

    return filters
end

-- Checks if a single group of conditions is satisfied (logical AND)
local function group_matches(group)
    ngx.log(ngx.DEBUG, "Evaluating group: ", cjson.encode(group))

    for _, condition in ipairs(group) do
        local actual_value = get_actual_value(condition.field)
        if actual_value == nil then
            ngx.log(ngx.ERR, "Missing actual value for field: ", condition.field)
            return false
        end

        local operator = condition.operator
        local expected = condition.value

        if operator == "match" then
            if not actual_value:match(expected) then
                ngx.log(ngx.DEBUG, "Condition failed (match): ", cjson.encode(condition))
                return false
            end

        elseif operator == "no_match" then
            if actual_value:match(expected) then
                ngx.log(ngx.DEBUG, "Condition failed (no_match): ", cjson.encode(condition))
                return false
            end

        elseif operator == "equal" then
            if actual_value ~= expected then
                ngx.log(ngx.DEBUG, "Condition failed (equal): ", cjson.encode(condition))
                return false
            end

        elseif operator == "no_equal" then
            if actual_value == expected then
                ngx.log(ngx.DEBUG, "Condition failed (no_equal): ", cjson.encode(condition))
                return false
            end

        else
            ngx.log(ngx.ERR, "Unsupported operator: ", operator)
            return false
        end
    end

    return true
end

-- Main filter evaluator (logical OR across groups)
local function check_filters(filters)
    for _, group in ipairs(filters) do
        if group_matches(group) then
            return true
        end
    end

    return false
end

--- Delete files older than `max_age_days` from `log_dir`
local function rotate_logs(log_dir, max_age_days)
    ngx.log(ngx.DEBUG, "Rotating logs in " .. log_dir .. " older than " .. max_age_days .. " days")

    local safe_dir = string.format("'%s'", log_dir:gsub("'", "'\\''"))
    local cmd = string.format("find %s -type f -mtime +%d -print -delete", safe_dir, max_age_days)
    local ok = os.execute(cmd)

    if not ok then
        ngx.log(ngx.ERR, "Failed to rotate logs with command: " .. cmd)
    else
        ngx.log(ngx.NOTICE, "Rotated logs older than " .. max_age_days .. " days in " .. log_dir)
    end
end

local function trim(s)
    return (s:gsub("^%s*(.-)%s*$", "%1"))
end

local function flatten_headers(header_table)
    local out = {}
    for k, v in pairs(header_table or {}) do
        if type(v) == "table" then
            for _, vv in ipairs(v) do
                table.insert(out, {
                    name = k,
                    value = vv
                })
            end
        else
            table.insert(out, {
                name = k,
                value = v
            })
        end
    end
    return out
end

local function empty_array()
    return setmetatable({}, {
        __newindex = function()
        end,
        __len = function()
            return 0
        end,
        __tostring = function()
            return "[]"
        end
    })
end

local function parse_cookie_header(header_value)
    local cookies = {}
    local list = type(header_value) == "table" and header_value or {header_value}

    for _, raw in ipairs(list) do
        local parts = {}
        for part in string.gmatch(raw, "[^;]+") do
            table.insert(parts, trim(part))
        end

        local first = table.remove(parts, 1)
        local name, value = first:match("^(.-)=(.*)$")
        if name and value then
            local cookie = {
                name = name,
                value = value,
                path = "",
                domain = "",
                httpOnly = false,
                secure = false
            }

            for _, attr in ipairs(parts) do
                local k, v = attr:match("^%s*([^=]+)=?(.*)$")
                if k then
                    k = k:lower()
                    if k == "path" then
                        cookie.path = v
                    elseif k == "domain" then
                        cookie.domain = v
                    elseif k == "httponly" then
                        cookie.httpOnly = true
                    elseif k == "secure" then
                        cookie.secure = true
                    end
                end
            end

            table.insert(cookies, cookie)
        end
    end

    if #cookies == 0 then
        return empty_array()
    end
    return cookies
end

local function parse_query_string(qs)
    local result = {}
    if type(qs) ~= "string" or qs == "" then
        return empty_array()
    end
    for k, v in string.gmatch(qs, "([^&=?]+)=([^&]*)") do
        table.insert(result, {
            name = k,
            value = v
        })
    end
    if #result == 0 then
        return empty_array()
    end
    return result
end

-- Main Function (exposed for external use)
local function main(log_dir, max_age_days, filters_string)
    ngx.log(ngx.DEBUG, "Using HAR_LOG_DIR: " .. log_dir)

    local filters = parse_filter_groups(filters_string)
    ngx.log(ngx.INFO, "Parsed filters: ", cjson.encode(filters))

    if not check_filters(filters) then
        ngx.log(ngx.DEBUG, "Request does not match any filter conditions, skipping HAR log")
        return
    end

    rotate_logs(log_dir, max_age_days)

    local now = os.date("*t")
    local ts = string.format("%04d-%02d-%02d_%02d_%02d_%02d_%03d", now.year, now.month, now.day, now.hour, now.min,
        now.sec, math.floor(ngx.now() % 1 * 1000))
    local uid = string.format("%04x", math.random(0, 0xfffff))

    local req = ngx.ctx._request_log or {}
    local resp_body = ngx.ctx._response_body or ""

    local log_data = {
        log = {
            version = "1.2",
            creator = {
                name = "d2-docker-network-logger",
                version = "1.0"
            },
            pages = {{
                startedDateTime = os.date("!%Y-%m-%dT%H:%M:%SZ"),
                id = "page_1",
                title = ngx.var.request_uri or "d2-docker-log",
                pageTimings = {}
            }},
            entries = {{
                pageRef = "page_1",
                startedDateTime = os.date("!%Y-%m-%dT%H:%M:%SZ"),
                time = ngx.now() - (req.timestamp or ngx.now()),
                request = {
                    method = req.method,
                    url = ngx.var.scheme .. "://" .. ngx.var.host .. ngx.var.request_uri,
                    httpVersion = "HTTP/1.1",
                    headers = flatten_headers(req.headers),
                    queryString = parse_query_string(ngx.var.query_string),
                    cookies = parse_cookie_header(req.headers and req.headers["cookie"]),
                    postData = req.body and {
                        mimeType = (req.headers and req.headers["content-type"]) or "",
                        text = req.body
                    } or nil,
                    headersSize = -1,
                    bodySize = req.body and #req.body or 0
                },
                response = {
                    status = ngx.status,
                    statusText = ngx.status == 200 and "OK" or "",
                    httpVersion = "HTTP/1.1",
                    headers = flatten_headers(ngx.resp.get_headers()),
                    cookies = parse_cookie_header(ngx.resp.get_headers()["set-cookie"]),
                    content = {
                        mimeType = ngx.header["Content-Type"] or "text/plain",
                        text = resp_body,
                        size = #resp_body
                    },
                    redirectURL = "",
                    headersSize = -1,
                    bodySize = #resp_body
                },
                cache = {},
                timings = {
                    send = 0,
                    wait = ngx.now() - (req.timestamp or ngx.now()),
                    receive = 0
                },
                serverIPAddress = ngx.var.server_addr,
                connection = tostring(ngx.var.connection)
            }}
        }
    }

    local filename = string.format("%s/%s-%s.har", log_dir, ts, uid)
    os.execute("mkdir -p " .. log_dir)
    local f = io.open(filename, "w")

    if f then
        ngx.log(ngx.INFO, "Write HAR: " .. filename)
        f:write(cjson.encode(log_data))
        f:close()
    else
        ngx.log(ngx.ERR, "Could not write HAR log file: " .. filename)
    end
end

local har_log_dir = os.getenv("HAR_LOG_DIR") or "/tmp/d2-docker-nginx-logs"
local max_age_days = tonumber(os.getenv("HAR_LOG_MAX_AGE_DAYS")) or 7
local filters_string = os.getenv("HAR_LOG_FILTERS") or ""

main(har_log_dir, max_age_days, filters_string)
