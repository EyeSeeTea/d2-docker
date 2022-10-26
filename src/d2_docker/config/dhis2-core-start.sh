#!/bin/bash -x
set -e -u -o pipefail
#
# Tasks:
#
#   - Run seed SQL files.
#   - Run pre-tomcat shell scripts.
#   - Start Tomcat Catalina.
#   - Run post-tomcat shell scripts
#

# Global: LOAD_FROM_DATA="yes" | "no"
# Global: DEPLOY_PATH=string
# Global: DHIS2_AUTH=string

export PGPASSWORD="dhis"

dhis2_url="http://localhost:8080/$DEPLOY_PATH"
dhis2_url_with_auth="http://$DHIS2_AUTH@localhost:8080/$DEPLOY_PATH"
psql_cmd="psql -v ON_ERROR_STOP=0 --quiet -h db -U dhis dhis2"
pgrestore_cmd="pg_restore -h db -U dhis -d dhis2"
configdir="/config"
homedir="/dhis2-home-files"
scripts_dir="/data/scripts"
root_db_path="/data/db"
post_db_path="/data/db/post"
source_apps_path="/data/apps"
source_documents_path="/data/document"
source_datavalues_path="/data/dataValue"
files_path="/DHIS2_home/files/"
tomcat_conf_dir="/usr/local/tomcat/conf"

debug() {
    echo "[dhis2-core-start] $*" >&2
}

run_sql_files() {
    base_db_path=$(test "${LOAD_FROM_DATA}" = "yes" && echo "$root_db_path" || echo "$post_db_path")
    debug "Files in data path"
    find "$base_db_path" >&2

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
        (cd "$(dirname "$path")" && bash -x "$path")
    done
}

run_post_scripts() {
    find "$scripts_dir" -type f -name '*.sh' -name 'post*' | sort | while read -r path; do
        debug "Run post-tomcat script: $path"
        (cd "$(dirname "$path")" && bash -x "$path" "$dhis2_url_with_auth")
    done
}

copy_apps() {
    debug "Copy Dhis2 apps: $source_apps_path -> $files_path"
    mkdir -p "$files_path/apps"
    if test -e "$source_apps_path"; then
        cp -Rv "$source_apps_path" "$files_path"
    fi
}

copy_documents() {
    debug "Copy Dhis2 documents: $source_documents_path -> $files_path"
    mkdir -p "$files_path/document"
    if test -e "$source_documents_path"; then
        cp -Rv "$source_documents_path" "$files_path"
    fi
}

copy_datavalues() {
    debug "Copy Dhis2 dataValues: $source_datavalues_path -> $files_path"
    mkdir -p "$files_path/dataValue"
    if test -e "$source_datavalues_path"; then
        cp -Rv "$source_datavalues_path" "$files_path"
    fi
}

copy_non_empty_files() {
    local from=$1 to=$2
    find "$from" -maxdepth 1 -type f -size +0 -exec cp -v {} "$to" \;
}

setup_tomcat() {
    debug "Setup tomcat"

    cp -v $configdir/DHIS2_home/* "/DHIS2_home/"
    cp -v $homedir/* /DHIS2_home/ || true
    copy_non_empty_files "$configdir/override/dhis2/" "/DHIS2_home/"

    cp -v "$configdir/server.xml" "$tomcat_conf_dir/server.xml"
    copy_non_empty_files "$configdir/override/tomcat/" "$tomcat_conf_dir/"
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
    while ! curl -sS -i "$dhis2_url" 2>/dev/null | grep "^Location"; do
        sleep 1
    done
}

INIT_DONE_FILE="/tmp/dhis2-core-start.done"

is_init_done() {
    test -e "$INIT_DONE_FILE"
}

init_done() {
    touch "$INIT_DONE_FILE"
}

run() {
    local host=$1 psql_port=$2

    setup_tomcat
    copy_apps
    copy_documents
    copy_datavalues

    if is_init_done; then
        debug "Container: already configured. Skip DB load"
    else
        debug "Container: clean. Load DB"
        wait_for_postgres
        run_sql_files || true
        run_pre_scripts || true
        init_done
    fi

    start_tomcat &
    wait_for_tomcat
    run_post_scripts || true
    debug "DHIS2 instance ready"
    wait
}

env
run "db" "5432"
