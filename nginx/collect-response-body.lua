-- Collect chunks of the response body
local chunk = ngx.arg[1]
local eof = ngx.arg[2]

ngx.ctx._response_body = (ngx.ctx._response_body or "") .. (chunk or "")
