#!/bin/bash
set -e -u -o pipefail
#
# Tasks:
#
#   - Run seed SQL files.
#   - Run pre-tomcat shell scripts.
#   - Start Tomcat Catalina.
#   - Run post-tomcat shell scripts
#

# Global LOAD_FROM_DATA="yes" | "no"

export PGPASSWORD="dhis"

dhis2_url="http://localhost:8080"
psql_cmd="psql -v ON_ERROR_STOP=0 --quiet -h db -U dhis dhis2"
pgrestore_cmd="pg_restore -h db -U dhis -d dhis2"
configdir="/config"
homedir="/dhis2-home-files"
scripts_dir="/data/scripts"
root_db_path="/data/db"
post_db_path="/data/db/post"
source_apps_path="/data/apps"
dest_apps_path="/DHIS2_home/files/"

debug() {
    echo "[dhis2-core-start] $*" >&2
}

run_sql_files() {
    base_db_path=$(test "${LOAD_FROM_DATA}" = "yes" && echo "$root_db_path" || echo "$post_db_path")

    find "$base_db_path" -type f \( -name '*.dump' \) |
        sort | while read -r path; do
        echo "Load SQL dump: $path"
        $pgrestore_cmd "$path" || true
    done

    find "$base_db_path" -type f \( -name '*.sql.gz' \) |
        sort | while read -r path; do
        echo "Load SQL (compressed): $path"
        zcat "$path" | $psql_cmd || true
    done

    find "$base_db_path" -type f \( -name '*.sql' \) |
        sort | while read -r path; do
        echo "Load SQL: $path"
        $psql_cmd <"$path" || true
    done
}

run_pre_scripts() {
    find "$scripts_dir" -type f -name '*.sh' ! \( -name 'post*' \) | sort | while read -r path; do
        debug "Run pre-tomcat script: $path"
        (cd "$(dirname "$path")" && bash "$path")
    done
}

run_post_scripts() {
    find "$scripts_dir" -type f -name '*.sh' -name 'post*' | sort | while read -r path; do
        debug "Run post-tomcat script: $path"
        (cd "$(dirname "$path")" && bash "$path")
    done
}

copy_apps() {
    debug "Copy Dhis2 apps: $source_apps_path -> $dest_apps_path"
    mkdir -p "$dest_apps_path/apps"
    if test -e "$source_apps_path"; then
        cp -Rv "$source_apps_path" "$dest_apps_path"
    fi
}

setup_tomcat() {
    cp -v "$configdir/DHIS2_home/dhis.conf" /DHIS2_home/dhis.conf
    cp -v $homedir/* /DHIS2_home/ || true
    cp -v "$configdir/server.xml" /usr/local/tomcat/conf/server.xml
}

wait_for_postgres() {
    debug "Waiting for postgres: ${host}:${psql_port}"
    while ! echo "select 1;" | $psql_cmd; do
        sleep 1
    done
}

start_tomcat() {
    debug "Start Tomcat catalina"
    catalina.sh run
}

wait_for_tomcat() {
    debug "Waiting for Tomcat to start: $dhis2_url"
    while ! curl -sS -i "$dhis2_url" 2>/dev/null | grep "Location: .*redirect.action"; do
        sleep 1
    done
}

run() {
    local host=$1 psql_port=$2
    setup_tomcat
    copy_apps
    wait_for_postgres
    run_sql_files || true
    run_pre_scripts || true
    start_tomcat &
    wait_for_tomcat
    run_post_scripts || true
    debug "DHIS2 instance ready"
    wait
}

env
run "db" "5432"
