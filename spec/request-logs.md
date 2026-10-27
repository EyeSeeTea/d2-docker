# Request logs

Task: https://app.clickup.com/t/8698vg4z1

Record selected HTTP requests (request + response) that go through the gateway, so we can inspect
what a client did against an instance without browser devtools.

## Usage

```shell
$ d2-docker start eyeseetea/dhis2-data:2.42-sierra-leone \
    --request-logs-rules rules.json --request-logs-dir ./request-logs
```

`rules.json`:

```json
{
    "maxAgeDays": 7,
    "maxBodyBytes": 1048576,
    "rules": [
        {
            "comment": "API errors",
            "status": { "match": "^[45]" },
            "url": { "match": "^/api/" }
        },
        {
            "comment": "Metadata imports, whatever the status",
            "method": "POST",
            "url": { "match": "^/api/(\\d+/)?metadata\\b" }
        }
    ]
}
```

## Rules

- `rules` is a list combined with OR. Inside a rule, fields are combined with AND.
- A field value is a string (shorthand for `equal`) or an object with one operator.
- An empty or missing `rules` list logs nothing. A rule with no fields matches every request.
- JSON instead of a string mini-language (`method==GET+status=~4..`): no parsing ambiguities, no
  shell quoting.
- `comment` (rule or top level) is ignored, use it to document the rule.

| Field    | Value                               |
| -------- | ----------------------------------- |
| `method` | `GET`, `POST`, ...                  |
| `url`    | Path + query string (request URI)   |
| `status` | Response status (string or integer) |

| Operator   | Meaning                        |
| ---------- | ------------------------------ |
| `equal`    | Exact match                    |
| `notEqual` | Not an exact match             |
| `match`    | PCRE regex (`ngx.re.find`)     |
| `notMatch` | PCRE regex does not match      |

## Output

- One HAR 1.2 file per logged request: `<DIR>/<YYYY-MM-DD_HH_MM_SS_mmm>-<METHOD>-<STATUS>-<rand>.har`
  (opens in Firefox/Chrome devtools, Network tab -> import).
- Includes request/response headers, query string, cookies and bodies.
- Bodies are truncated to `maxBodyBytes` (default 1 MiB); the HAR entry `comment` flags it.
  Non-UTF-8 bodies (images, ...) are stored base64-encoded.
- Files older than `maxAgeDays` are deleted (default 7).

Secrets are redacted (`<redacted>`) before writing:

- Header values: `Authorization`, `Cookie`, `Set-Cookie` (and the HAR `cookies` arrays).
- JSON and form bodies: values of keys matching `password` (case-insensitive). Covers login
  (`/api/auth/login`), user create/update and password changes.

## Access

`d2-docker request-logs [DIRECTORY]` lists, filters and merges the HAR files. Without `DIRECTORY`,
it uses the logs directory mounted in the running instance gateway.

```shell
$ d2-docker request-logs --since "2026-10-27 08:00" --status 4 --user admin
2026-10-27 08:57:51  405  GET     admin            /api/dataElements/nope
$ d2-docker request-logs --method POST --url metadata --merge imports.har
```

- Filters: `--since`/`--until` (`YYYY-MM-DD[ HH:MM[:SS]]`), `--method`, `--status` (regex, anchored
  at start), `--url` (regex on path + query), `--user`. Time, method and status come from the
  filename, so only files passing those filters are opened.
- Output: table (default), `--files` (paths only, for `rsync --files-from`), or `--merge FILE` (one
  HAR with all matching entries, in order).
- Each HAR entry has a custom `_user` field (HAR allows `_`-prefixed fields) besides the `comment`.
- Remote servers: run the command there and copy the merged file (`ssh` + `scp`).

## Implementation notes

- Code layout:

  | File                                     | Responsibility                                        |
  | ---------------------------------------- | ----------------------------------------------------- |
  | `config/gateway/request_logs.lua`        | nginx phase handlers, write and rotate HAR files      |
  | `config/gateway/request_logs/rules.lua`  | Parse/validate the rules file, match requests (pure)  |
  | `config/gateway/request_logs/har.lua`    | Build HAR documents, redact secrets (pure)            |
  | `config/gateway/request_logs/users.lua`  | Resolve the username (core lookup + cache)            |
  | `config/gateway/request_logs/http.lua`   | Header and cookie helpers                             |
  | `config/gateway/start.sh`                | Start OpenResty with workers as the host user         |
  | `d2_docker/request_logs.py`              | Validate rules (start), read/filter/merge HAR files   |
  | `d2_docker/commands/request_logs.py`     | `request-logs` command: arguments and output          |
  | `test/request-logs/`                     | Unit tests (Lua + Python) with shared cases           |

- The gateway always runs OpenResty (nginx + Lua), with or without request logs: one image and one
  `nginx.conf`. Without a rules file, the hooks do nothing. Config path:
  `/usr/local/openresty/nginx/conf/nginx.conf`. Mount the rules file and the logs directory.
- `d2-docker start` validates the rules structure before starting; the gateway validates it again
  (plus regexes) in `init_by_lua` and refuses to start on errors.
- Workers run as the host user that ran `d2-docker start` (uid/gid passed as `GATEWAY_UID`/`GATEWAY_GID`;
  `gateway/start.sh` creates a matching user), so they can write into the mounted host directory and
  the HAR files belong to that user. Not root: they handle untrusted HTTP. Fallbacks: uid 0 -> root,
  no uid -> nobody.
- Rules are read on gateway start; changing them requires restarting the gateway.
- Bodies: stop accumulating at `maxBodyBytes`. Request bodies above `client_body_buffer_size` are
  in a temp file (`ngx.req.get_body_data()` returns nil): read it with `ngx.req.get_body_file()`.
- Hooks: `access_by_lua` (capture request + body), `body_filter_by_lua` (accumulate response body),
  `log_by_lua` (evaluate rules, write HAR). A working prototype (Lua + HAR writer) is on branch
  `feature/nginx-logs-8698vg4z1`, folder `nginx/`.
- Regexes with `ngx.re` (PCRE), not Lua patterns (no `\d`, no `|`).
- Method: take it from the request line (`$request`): `error_page` redirects (502 -> `/50x.html`)
  change `ngx.req.get_method()` to GET.
- Skip buffering the response body when no rule can match from method/url alone (status is only
  known later).
- Run log rotation from a periodic `ngx.timer.every`, not on every logged request.
- README: document the options, the rules format and an example.

## User

Each HAR entry stores the username in its `comment` (`user=NAME`). It is resolved when the request is logged (its
session is alive at that moment) and written into the file, so logs stay readable after the session
expires. DHIS2 keeps sessions in memory, so the gateway asks it, only for requests that will be logged:

- `Authorization: Basic`: decode it locally (calling DHIS2 with it would create a new session).
- Other `Authorization` (`ApiToken`, `Bearer`) or `Cookie: JSESSIONID`:
  `GET http://core:8080/<DEPLOY_PATH>/api/me?fields=username` with the same header, sent with
  `X-Requested-With: XMLHttpRequest` (invalid session -> 401, not 302). Cache
  `sha256(credential) -> username` in a `lua_shared_dict` (TTL 1h; failures 1m).
- Login (no credentials yet): same lookup with the `JSESSIONID` of the response `Set-Cookie`.
- No credentials or lookup fails (e.g. request sent with an already expired session): no username.
  Exception: a session looked up in the last hour is still in the cache, so a request sent after
  it expired (or after logout) shows the user that owned it.

The lookup uses cosockets, which are not available in `log_by_lua`: run lookup + HAR write in an
`ngx.timer.at(0, ...)` callback.

## Testing

- No regressions with OpenResty and no rules file: gzip, static apps (`/data/apps`), `50x.html`.
- Logged bodies are readable text, not gzip (nginx gzip filter and/or core compression).
- Large request body (e.g. a metadata import of a few MB) is logged (temp file path), truncated.
- Workers can write into the mounted logs directory.
- Secrets redacted: login, Basic auth, user creation with password.
- Username resolved for session, Basic auth and API token requests.
