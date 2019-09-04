#!/bin/sh
set -e -u

psql_cmd="${psql[@]} -v ON_ERROR_STOP=0 --quiet"
base_db_path="/data/db.sql.gz"
post_sql_dir="/data/post-sql"

if test -e /data; then
    {
        test "$LOAD_FROM_DATA" = "yes" && echo $base_db_path || true;
        find $post_sql_dir -type f | sort;
        } | while read path; do
        echo "[load-database] Load SQL: $path"
        case "$path" in
            *.gz) zcat "$path" | $psql_cmd;;
            *) cat "$path" | $psql_cmd;;
        esac
    done
fi
