local cjson = require "cjson.safe"

ngx.req.read_body()

local req = {
    timestamp = ngx.now(),
    method = ngx.req.get_method(),
    url = ngx.var.request_uri,
    headers = ngx.req.get_headers(),
    body = ngx.req.get_body_data()
}

-- store request in context to process later in log-response.lua
ngx.ctx._request_log = req
