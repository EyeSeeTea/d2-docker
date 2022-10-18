#!/bin/bash -x
set -e -u -o pipefail

get_script_dir() {
    (cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
}

expose_d2_docker_to_host() {
    script_dir=$(get_script_dir)
    cp -av "$script_dir/../src/d2_docker/." "/app/shared/d2-docker"
}

start_api() {
    d2-docker api start
}

fix_volumes_ownership() {
    if test "$VOLUMES_OWNERSHIP" -a "$VOLUMES_OWNERSHIP" != ":"; then
        chown -R "$VOLUMES_OWNERSHIP" /app/shared/
    fi
}

main() {
    expose_d2_docker_to_host
    fix_volumes_ownership
    start_api
}

main
