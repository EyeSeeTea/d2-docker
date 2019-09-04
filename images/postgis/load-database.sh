#!/bin/sh
set -e -u

if test "$LOAD_FROM_DATA" = "yes"; then
    if test -e /data; then
        echo "Load SQL files: $(ls /data)"
        zcat /data/*.sql.gz | "${psql[@]}" -v ON_ERROR_STOP=0 --quiet
    fi
fi
