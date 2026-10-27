-- Record selected requests (request + response) as HAR files. See spec/request-logs.md
--
-- Entry points for the nginx phases (nginx.conf). Logic lives in request_logs/*.lua:
-- rules (parse + match), har (build + redact), users (resolve username), http (headers/cookies).

local cjson = require "cjson.safe"
local rules = require "request_logs.rules"
local har = require "request_logs.har"
local users = require "request_logs.users"

local _M = {}

local RULES_PATH = "/etc/d2-docker/request-logs.json"
local LOGS_DIR = "/var/log/d2-docker/requests"

local config -- nil: request logs disabled

-- Local time, parsed by d2_docker/request_logs.py (FILENAME_RE); keep in sync
local function filename_time(seconds)
    local ms = math.floor((seconds % 1) * 1000)
    return os.date("%Y-%m-%d_%H_%M_%S", math.floor(seconds)) .. string.format("_%03d", ms)
end

-- error_page redirects (i.e. 502 -> /50x.html) change the method to GET: use the request line
local function original_method()
    return ngx.var.request:match("^(%S+)") or ngx.req.get_method()
end

local function read_request_body(max_bytes)
    ngx.req.read_body()
    local data = ngx.req.get_body_data()

    if not data then
        -- Large bodies are buffered into a temp file
        local path = ngx.req.get_body_file()
        local file = path and io.open(path, "rb")
        if file then
            data = file:read(max_bytes + 1)
            file:close()
        end
    end

    if data and #data > max_bytes then
        return data:sub(1, max_bytes), true
    else
        return data, false
    end
end

local function write_har(premature, capture)
    if premature then return end

    local username = users.resolve(capture.request_headers, capture.response_headers)
    local filename = string.format("%s/%s-%s-%d-%04x.har", LOGS_DIR, filename_time(capture.started),
        capture.method, capture.status, math.random(0, 0xffff))

    local file, err = io.open(filename, "w")
    if not file then
        ngx.log(ngx.ERR, "Request logs: cannot write ", filename, ": ", err)
        return
    end
    file:write(cjson.encode(har.build(capture, username)))
    file:close()
end

local function rotate_logs(premature)
    if premature then return end

    -- Safe because LOGS_DIR is a constant: a configurable path would make this
    -- format string a shell injection
    local command = string.format("find %s -maxdepth 1 -name '*.har' -mmin +%d -delete",
        LOGS_DIR, config.maxAgeDays * 24 * 60)
    if not os.execute(command) then
        ngx.log(ngx.ERR, "Request logs: rotation failed: ", command)
    end
end

-- Phases

function _M.init()
    local file = io.open(RULES_PATH, "r")
    local text = file and file:read("*a")
    if file then file:close() end

    if not text or text:match("^%s*$") then return end

    local ok, result = pcall(rules.parse, text)
    if not ok then error("Request logs: invalid rules (" .. RULES_PATH .. "): " .. result, 0) end

    config = result
    ngx.log(ngx.NOTICE, "Request logs: enabled, rules: ", #config.rules)
end

function _M.init_worker()
    if not config then return end

    math.randomseed(ngx.now() * 1000 + ngx.worker.pid())

    if ngx.worker.id() == 0 then
        ngx.timer.at(0, rotate_logs)
        ngx.timer.every(3600, rotate_logs)
    end
end

function _M.access()
    if not config then return end

    -- Status is not known yet: discard only the requests that cannot match any rule
    local values = { method = original_method(), url = ngx.var.request_uri }
    if not rules.match(config.rules, values) then return end

    local body, truncated = read_request_body(config.maxBodyBytes)
    ngx.ctx.request_logs = {
        started = ngx.req.start_time(),
        request_body = body,
        request_body_truncated = truncated,
        response_chunks = {},
        response_body_size = 0,
    }
end

function _M.body_filter()
    local ctx = ngx.ctx.request_logs
    local chunk = ngx.arg[1]
    if not ctx or not chunk or chunk == "" then return end

    local room = config.maxBodyBytes - ctx.response_body_size
    if room > 0 then
        table.insert(ctx.response_chunks, chunk:sub(1, room))
    end
    ctx.response_body_size = ctx.response_body_size + #chunk
end

function _M.log()
    local ctx = ngx.ctx.request_logs
    if not ctx then return end

    local method = original_method()
    local values = { method = method, url = ngx.var.request_uri, status = tostring(ngx.status) }
    if not rules.match(config.rules, values) then return end

    -- ngx.var/ngx.req are not available in timers: capture everything here
    local capture = {
        started = ctx.started,
        time_ms = math.floor(tonumber(ngx.var.request_time) * 1000),
        method = method,
        url = ngx.var.scheme .. "://" .. (ngx.var.http_host or ngx.var.host) .. ngx.var.request_uri,
        query_string = ngx.var.query_string,
        http_version = ngx.var.server_protocol,
        status = ngx.status,
        server_address = ngx.var.server_addr,
        request_headers = ngx.req.get_headers(0),
        request_body = ctx.request_body,
        request_body_truncated = ctx.request_body_truncated,
        request_body_size = tonumber(ngx.var.content_length) or (ctx.request_body and #ctx.request_body or 0),
        response_headers = ngx.resp.get_headers(0),
        response_body = table.concat(ctx.response_chunks),
        response_body_truncated = ctx.response_body_size > config.maxBodyBytes,
        response_body_size = ctx.response_body_size,
    }

    -- Cosockets (user lookup) are not available in the log phase: write from a timer
    local ok, err = ngx.timer.at(0, write_har, capture)
    if not ok then ngx.log(ngx.ERR, "Request logs: cannot create timer: ", err) end
end

return _M
