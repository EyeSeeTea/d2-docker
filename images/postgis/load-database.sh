#!/bin/sh
set -e

if test -e /data; then
    zcat /data/*.sql.gz | "${psql[@]}" -v ON_ERROR_STOP=0 --quiet
fi
