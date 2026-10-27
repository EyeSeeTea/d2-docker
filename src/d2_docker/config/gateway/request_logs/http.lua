-- Header and cookie helpers shared by the request logs modules

local _M = {}

-- ngx.req.get_headers()/ngx.resp.get_headers() return a string, or a table for repeated headers
function _M.values(header_value)
    return type(header_value) == "table" and header_value or { header_value }
end

function _M.get(headers, name)
    return _M.values(headers[name])[1]
end

local function add_cookies(cookies, text)
    for part in text:gmatch("[^;]+") do
        local name, value = part:match("^%s*([^=]+)=(.*)$")
        if name then table.insert(cookies, { name = name, value = value }) end
    end
end

-- Cookie: "a=1; b=2"
function _M.request_cookies(header_value)
    local cookies = {}
    for _, single in ipairs(_M.values(header_value)) do
        add_cookies(cookies, single)
    end
    return cookies
end

-- Set-Cookie: "a=1; Path=/; HttpOnly" (one header per cookie, attributes after the first ";")
function _M.response_cookies(header_value)
    local cookies = {}
    for _, single in ipairs(_M.values(header_value)) do
        add_cookies(cookies, single:match("^[^;]*"))
    end
    return cookies
end

return _M
