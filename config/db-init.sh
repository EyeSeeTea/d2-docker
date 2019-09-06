#!/bin/bash
set -e -u -o pipefail
psql_cmd="psql -v ON_ERROR_STOP=0 --quiet -U dhis dhis2"
base_db_path="/data/db"

load_database() {
    if test -e "$base_db_path"; then
        find "$base_db_path" -type f | sort | while read path; do
            echo "Load SQL: $path"
            case "$path" in
                *.gz) zcat "$path" | $psql_cmd || true;;
                *) cat "$path" | $psql_cmd || true;;
            esac
        done
    fi
}

load_database
