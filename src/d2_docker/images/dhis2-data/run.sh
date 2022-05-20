#!/bin/bash
set -e -u

# Global: VOLUME="/path/to/destination"
# Global: LOAD_FROM_DATA="yes" | "no"

main() { local volume=$1
    if test "$LOAD_FROM_DATA" = "yes"; then
        cp -av /data/* $volume
        chmod -R u+rwX,go+rX,go-w $volume
    else
        rm -rf /$volume/*
    fi
}

env
main $VOLUME
