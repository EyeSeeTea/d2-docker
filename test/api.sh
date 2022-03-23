#!/bin/bash

url="http://localhost:5000"
image="docker.eyeseetea.com/eyeseetea/dhis2-data:2.34-play"
image2="${image}2"

debug() {
    echo "$@" >&2
}

get() {
    local path=$1
    debug "GET $path"
    curl -f -sS "${url}${path}"
}

post() {
    local path=$1
    local data0=$2
    export $(compgen -v)
    data=$(envsubst <<<"$data0" | jq)
    debug "POST $path $data"
    curl -f -X POST -sS -H "Content-Type: application/json" "${url}${path}" -d "$data"
}

harbor_api="$url/harbor/https://docker.eyeseetea.com/api/v2.0"

run_tests() {
    curl -sS "$harbor_api/quotas/2" | jq
    curl -sS -H "Content-Type: application/json" \
        -X PUT "$harbor_api/quotas/2" -d '{"hard": {"storage": 161061273600}}'

    get "/version"
    get "/instances"

    post "/instances/pull" '{"image": "$image"}'
    post "/instances/stop" '{"image": "$image"}'
    post "/instances/start" '{"image": "$image", "detach": true, "port": 9999}'
    get "/instances"
    while ! curl -f "http://localhost:9999" 2>/dev/null; do sleep 1; done

    post "/instances/commit" '{"image": "$image"}'
    post "/instances/copy" '{"source": "$image", "destinations": ["$image2"]}'
    post "/instances/push" '{"image": "$image2"}'
    post "/instances/stop" '{"image": "$image"}'
    post "/instances/rm" '{"images": ["$image2"]}'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    set -e -u -o pipefail
    run_tests
fi
