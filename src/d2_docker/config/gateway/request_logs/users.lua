-- Resolve the DHIS2 user of a request. See spec/request-logs.md (User)
--
-- DHIS2 keeps sessions in memory, so sessions and tokens are looked up in core (/api/me). The
-- username is resolved when the request is logged (its session is alive) and cached for an hour.

local cjson = require "cjson.safe"
local resty_sha256 = require "resty.sha256"
local resty_string = require "resty.string"
local http = require "request_logs.http"

local _M = {}

local CORE_HOST = "core"
local CORE_PORT = 8080
local CACHE_TTL = 3600
local CACHE_TTL_FAILED = 60
local DEPLOY_PATH = os.getenv("DEPLOY_PATH") or "" -- read in init_by_lua (needs `env DEPLOY_PATH`)

local function sha256_hex(text)
    local sha256 = resty_sha256:new()
    sha256:update(text)
    return resty_string.to_hex(sha256:final())
end

-- Raw socket instead of resty.http: bundling the library for a single GET is not worth it.
-- The request is HTTP/1.0 on purpose: the connection closes after the response, so
-- receive("*a") terminates without parsing Content-Length or chunks.
local function fetch_username(header_name, header_value)
    local sock = ngx.socket.tcp()
    sock:settimeout(5000)

    local ok, err = sock:connect(CORE_HOST, CORE_PORT)
    if not ok then
        ngx.log(ngx.ERR, "Request logs: cannot connect to core: ", err)
        return nil
    end

    -- X-Requested-With: invalid session -> 401 (instead of a 302 to the login page)
    sock:send(table.concat({
        "GET " .. DEPLOY_PATH .. "/api/me?fields=username HTTP/1.0",
        "Host: " .. CORE_HOST,
        "Accept: application/json",
        "X-Requested-With: XMLHttpRequest",
        header_name .. ": " .. header_value,
        "",
        "",
    }, "\r\n"))

    local status_line = sock:receive("*l")
    local body

    local status = status_line and status_line:match("^HTTP/%d%.%d (%d+)")
    if status == "200" then
        repeat
            local header_line = sock:receive("*l")
        until not header_line or header_line == ""
        body = sock:receive("*a")
    end
    sock:close()

    local data = body and cjson.decode(body)
    return type(data) == "table" and type(data.username) == "string" and data.username or nil
end

-- Failed lookups are cached too (shorter), so a burst of requests with an expired session
-- does not hit core every time
local function lookup_username(header_name, header_value)
    local cache = ngx.shared.request_logs_users
    local key = sha256_hex(header_name .. ":" .. header_value)
    local cached = cache:get(key)
    if cached ~= nil then return cached ~= "" and cached or nil end

    local username = fetch_username(header_name, header_value)
    cache:set(key, username or "", username and CACHE_TTL or CACHE_TTL_FAILED)
    return username
end

local function find_session_id(cookies)
    for _, cookie in ipairs(cookies) do
        if cookie.name == "JSESSIONID" then return cookie.value end
    end
end

-- Return the username of the request, or nil if unknown. Uses cosockets: not callable in the log phase.
function _M.resolve(request_headers, response_headers)
    local authorization = http.get(request_headers, "authorization")

    if authorization then
        local basic = authorization:match("^[Bb]asic%s+(%S+)")
        if basic then
            -- Decode locally: calling DHIS2 with Basic auth would create a new session
            local decoded = ngx.decode_base64(basic)
            return decoded and decoded:match("^([^:]*):")
        else
            return lookup_username("Authorization", authorization)
        end
    end

    local session_id = find_session_id(http.request_cookies(request_headers["cookie"]))
    local username = session_id and lookup_username("Cookie", "JSESSIONID=" .. session_id)
    if username then return username end

    -- Session created by this request (i.e. login)
    local new_session_id = find_session_id(http.response_cookies(response_headers["set-cookie"]))
    return new_session_id and lookup_username("Cookie", "JSESSIONID=" .. new_session_id) or nil
end

return _M
