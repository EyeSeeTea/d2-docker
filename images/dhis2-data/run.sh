#!/bin/sh
set -e -u

main() { local volume=$1
    cp -av /data/* "$volume"
}

env
main $VOLUME
