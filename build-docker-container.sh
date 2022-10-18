#!/bin/bash
set -e -u -o pipefail

image_name="eyeseetea/d2-docker-container"
version=$(./d2-docker-dev.sh version | grep "^d2-docker" | awk '{print $3}')
docker build -t "$image_name:$version" .
docker image tag "$image_name:$version" "$image_name:latest"
