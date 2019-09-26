#!/bin/sh
set -e -u

# Global LOAD_FROM_DATA="yes" | "no"

main() { local volume=$1
    if test "$LOAD_FROM_DATA" = "yes"; then
        cp -av /data/* $volume
        chmod -R o+r $volume
    else
        rm -rf /$volume/*
    fi
}

env
main $VOLUME
