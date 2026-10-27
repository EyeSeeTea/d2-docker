#!/bin/bash
# Unit tests for request logs: gateway Lua module (in an OpenResty container) + rules validation in Python.
set -e -u -o pipefail

test_dir=$(cd "$(dirname "$0")" && pwd)
root_dir=$(cd "$test_dir/../.." && pwd)
# The -fat variant includes the `resty` CLI (needs Perl), same OpenResty version as the gateway
image="openresty/openresty:1.27.1.2-alpine-fat"

docker run --rm -v "$root_dir:/d2-docker:ro" "$image" resty /d2-docker/test/request-logs/test_rules.lua

PYTHONPATH="$root_dir/src" python3 -m unittest discover -s "$test_dir" -p "test_*.py"
