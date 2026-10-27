-- Build HAR 1.2 documents from captured requests, with secrets redacted. See spec/request-logs.md

local cjson = require "cjson.safe"
local http = require "request_logs.http"

local _M = {}

local REDACTED = "<redacted>"
local REDACTED_HEADERS = { authorization = true, cookie = true, ["set-cookie"] = true }
local PASSWORD_JSON_RE = [[("[^"]*password[^"]*"\s*:\s*)"(?:[^"\\]|\\.)*"]]
local PASSWORD_FORM_RE = [[((?:^|&)[^=&]*password[^=&]*=)[^&]*]]

-- HAR lists must be encoded as [] even when empty (cjson defaults to {})
local function empty_array()
    return setmetatable({}, cjson.empty_array_mt)
end

-- Redact the values of keys matching "password" in JSON and form bodies
function _M.redact_body(body, mime_type)
    if not body or body == "" then return body end

    if (mime_type or ""):find("x-www-form-urlencoded", 1, true) then
        return (ngx.re.gsub(body, PASSWORD_FORM_RE, "$1" .. REDACTED, "ijo"))
    else
        return (ngx.re.gsub(body, PASSWORD_JSON_RE, '$1"' .. REDACTED .. '"', "ijo"))
    end
end

local function har_time(seconds)
    local ms = math.floor((seconds % 1) * 1000)
    return os.date("!%Y-%m-%dT%H:%M:%S", math.floor(seconds)) .. string.format(".%03dZ", ms)
end

local function har_headers(headers)
    local out = empty_array()
    for name, value in pairs(headers) do
        for _, single in ipairs(http.values(value)) do
            local redacted = REDACTED_HEADERS[name:lower()] and REDACTED or single
            table.insert(out, { name = name, value = redacted })
        end
    end
    return out
end

local function har_cookies(cookies)
    local out = empty_array()
    for _, cookie in ipairs(cookies) do
        table.insert(out, { name = cookie.name, value = REDACTED })
    end
    return out
end

local function har_query_string(query_string)
    local out = empty_array()
    for name, value in pairs(ngx.decode_args(query_string or "", 0)) do
        for _, single in ipairs(http.values(value)) do
            table.insert(out, { name = name, value = tostring(single) })
        end
    end
    return out
end

local function is_valid_utf8(text)
    local _, _, err = ngx.re.find(text, "", "ujo")
    return not err
end

-- Binary bodies (images, ...) are not valid JSON strings: store them base64-encoded
local function har_content(text, mime_type)
    local content = { mimeType = mime_type or "", size = text and #text or 0 }
    if text and text ~= "" then
        if is_valid_utf8(text) then
            content.text = text
        else
            content.text = ngx.encode_base64(text)
            content.encoding = "base64"
        end
    end
    return content
end

local function comment(capture, username)
    local parts = {}
    if username then table.insert(parts, "user=" .. username) end
    if capture.request_body_truncated then table.insert(parts, "request body truncated") end
    if capture.response_body_truncated then table.insert(parts, "response body truncated") end
    return table.concat(parts, ", ")
end

-- Build a HAR document with a single entry from a request captured in the log phase
function _M.build(capture, username)
    local request_mime_type = http.get(capture.request_headers, "content-type")
    local response_mime_type = http.get(capture.response_headers, "content-type")

    local entry = {
        startedDateTime = har_time(capture.started),
        time = capture.time_ms,
        comment = comment(capture, username),
        _user = username, -- custom field (HAR allows _-prefixed), read by d2_docker/request_logs.py
        request = {
            method = capture.method,
            url = capture.url,
            httpVersion = capture.http_version,
            headers = har_headers(capture.request_headers),
            queryString = har_query_string(capture.query_string),
            cookies = har_cookies(http.request_cookies(capture.request_headers["cookie"])),
            headersSize = -1,
            bodySize = capture.request_body_size,
        },
        response = {
            status = capture.status,
            statusText = "",
            httpVersion = capture.http_version,
            headers = har_headers(capture.response_headers),
            cookies = har_cookies(http.response_cookies(capture.response_headers["set-cookie"])),
            content = har_content(_M.redact_body(capture.response_body, response_mime_type), response_mime_type),
            redirectURL = http.get(capture.response_headers, "location") or "",
            headersSize = -1,
            bodySize = capture.response_body_size,
        },
        cache = {},
        timings = { send = 0, wait = capture.time_ms, receive = 0 },
        serverIPAddress = capture.server_address,
    }

    if capture.request_body then
        entry.request.postData = {
            mimeType = request_mime_type or "",
            text = _M.redact_body(capture.request_body, request_mime_type),
        }
    end

    return {
        log = {
            version = "1.2",
            creator = { name = "d2-docker", version = "1.0" },
            entries = { entry },
        }
    }
end

return _M
