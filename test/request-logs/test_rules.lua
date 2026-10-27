-- Unit tests for the gateway request logs modules (rules + redaction). Run: test/request-logs/run.sh

local test_dir = arg[0]:match("^(.*)/[^/]*$") or "."
package.path = test_dir .. "/../../src/d2_docker/config/gateway/?.lua;" .. package.path

local cjson = require "cjson.safe"
local rules = require "request_logs.rules"
local har = require "request_logs.har"

-- Keep [] and {} apart when re-encoding the configs of the cases
local json = cjson.new()
json.decode_array_with_array_mt(true)

local passed, failed = 0, 0

local function check(ok, description)
    if ok then
        passed = passed + 1
    else
        failed = failed + 1
        print("✘ " .. description)
    end
end

local function read_file(path)
    local file = assert(io.open(path, "r"))
    local text = file:read("*a")
    file:close()
    return text
end

local function config_text(case)
    return case.configText or json.encode(case.config)
end

local cases = assert(json.decode(read_file(test_dir .. "/rules-cases.json")))

-- Rules

for _, case in ipairs(cases.matching) do
    local ok, config = pcall(rules.parse, config_text(case))
    check(ok, case.comment .. ": config should be valid: " .. tostring(config))

    if ok then
        for _, request in ipairs(case.requests) do
            local values = { method = request.method, url = request.url, status = request.status }
            local matched = rules.match(config.rules, values)
            local description = string.format("%s: %s %s %s -> expected %s",
                case.comment, request.method, request.url, request.status or "(no status)", tostring(request.expected))
            check(matched == request.expected, description)
        end
    end
end

for _, case in ipairs(cases.invalid) do
    local ok, err = pcall(rules.parse, config_text(case))
    check(not ok, case.comment .. ": config should be invalid")
    if not ok and case.error then
        local description = string.format("%s: error should contain %q (got %q)", case.comment, case.error, err)
        check(err:find(case.error, 1, true) ~= nil, description)
    end
end

-- Redaction

local redactions = {
    { "application/json", '{"username":"admin","password":"district"}', '{"username":"admin","password":"<redacted>"}' },
    { "application/json", '{"userCredentials":{"password": "a\\"b"},"x":1}', '{"userCredentials":{"password": "<redacted>"},"x":1}' },
    { "application/json", '{"oldPassword":"a","newPassword":"b"}', '{"oldPassword":"<redacted>","newPassword":"<redacted>"}' },
    { "application/json;charset=UTF-8", '{"PASSWORD":"a"}', '{"PASSWORD":"<redacted>"}' },
    { "application/x-www-form-urlencoded", "j_username=admin&j_password=district&x=1", "j_username=admin&j_password=<redacted>&x=1" },
    { "application/x-www-form-urlencoded", "password=a", "password=<redacted>" },
    { "application/json", '{"name":"password reset","x":"a=b"}', '{"name":"password reset","x":"a=b"}' },
}

for _, redaction in ipairs(redactions) do
    local mime_type, body, expected = unpack(redaction)
    local actual = har.redact_body(body, mime_type)
    check(actual == expected, string.format("redact %s %s -> %s (got %s)", mime_type, body, expected, actual))
end

print(string.format("Lua: %d passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
