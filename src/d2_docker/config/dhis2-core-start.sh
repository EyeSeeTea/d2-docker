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
# Global: LOAD_DUMP_FROM_DATA="yes" | "no"
# Global: EXTERNAL_DB_URL=string (optional)
# Global: DEPLOY_PATH=string
# Global: DHIS2_AUTH=string

export PGPASSWORD="dhis"
db_url=""
if [[ -n "$EXTERNAL_DB_URL" ]]; then
    db_url="${EXTERNAL_DB_URL//localhost/host.docker.internal}"
fi

# Default to 10 seconds
[[ "$STOP_GRACE_PERIOD" =~ ^[0-9]+$ ]] || STOP_GRACE_PERIOD=10

DEPLOY_PATH=${DEPLOY_PATH#/}

dhis2_url="http://localhost:8080/$DEPLOY_PATH"
dhis2_url_with_auth="http://$DHIS2_AUTH@localhost:8080/$DEPLOY_PATH"
psql_base_cmd="psql --quiet ${db_url:-"-h db -U dhis dhis2"}"
psql_cmd="$psql_base_cmd -v ON_ERROR_STOP=0"
psql_strict_cmd="$psql_base_cmd -v ON_ERROR_STOP=1"
pgrestore_cmd="pg_restore ${db_url:-"-h db -U dhis -d dhis2"}"
configdir="/config"
homedir="/dhis2-home-files"
scripts_dir="/data/scripts"
root_db_path="/data/db"
post_db_path="/data/db/post"
source_apps_path="/data/apps"
source_documents_path="/data/document"
source_datavalues_path="/data/dataValue"
home_path="/DHIS2_home"
files_path="$home_path/files/"
tomcatdir=/usr/local/tomcat
tomcat_conf_dir="$tomcatdir/conf"
approot="$tomcatdir/webapps/ROOT"
flag_sql_error="$home_path/flag-sql-error"


debug() {
    echo "[dhis2-core-start] $*" >&2
}

setup_error_page() {
    debug "Setting up error page (application removed)"
    rm -rf "$approot"
    mkdir -p -m 750 "$approot"
    chown tomcat:tomcat "$approot"
    echo '<!DOCTYPE html><title>Error</title>
    Error during preparation of the service' > "$approot/index.html"
}

run_sql_files() {
    if { [ -z "$db_url" ] && [ "${LOAD_FROM_DATA}" = "yes" ]; } ||
        { [ -n "$db_url" ] && [ "${LOAD_FROM_DATA}" = "yes" ] && [ "${LOAD_DUMP_FROM_DATA}" = "yes" ]; }; then
        base_db_path="$root_db_path"
    else
        base_db_path="$post_db_path"
    fi
    debug "Files in data path"
    if [[ ! -d "$base_db_path" ]] ; then
        debug " -- NO FILES -- "
        return 0
    fi
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

    local sql_error=0
    while read -r path; do
        echo "Load SQL: $path"
        exit_code=0
        run_psql_cmd "$path" || exit_code=$?
        if [ "$exit_code" -gt 0 ]; then
            echo "Exit code: $exit_code"
            sql_error=1
            break
        fi
    done < <(find "$base_db_path" -type f \( -name '*.sql' \) | sort)

    if [ "$sql_error" -gt 0 ]; then
        touch "$flag_sql_error"
        setup_error_page
        return 1
    fi
    return 0
}

run_psql_cmd() {
    local path=$1
    if [[ "$path" == *strict* ]]; then
        echo "Strict mode: $path"
        $psql_strict_cmd < "$path"
    else
        echo "Normal mode: $path"
        $psql_cmd < "$path"
    fi
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

    cp -v $configdir/DHIS2_home/* "$home_path/"
    cp -v $homedir/* $home_path/ || true
    copy_non_empty_files "$configdir/override/dhis2/" "$home_path/"

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

manage_tomcat_lifecycle() {
    local msg="${1:-}"
    local callback="${2:-}"

    start_tomcat &
    LAST_PID=$!

    if [ -n "$callback" ]; then
        $callback
    fi

    [ -n "$msg" ] && debug "$msg"
    
    wait $LAST_PID || true
}

wait_for_tomcat() {
    debug "Waiting for Tomcat to start: $dhis2_url"
    while ! curl -sS -i "$dhis2_url" 2>/dev/null | grep "^Location"; do
        sleep 1
    done
}

cleanup() {
    debug "--- [SIGNAL RECEIVED] ---"
    debug "Stopping tomcat"
    catalina.sh stop &
    STOP_PID=$!
    count=0
    while [ $count -lt $STOP_GRACE_PERIOD ]; do
        if ! kill -0 $STOP_PID 2>/dev/null; then
            debug "Tomcat has stopped."
            exit 0
        fi
        sleep 1
        count=$((count + 1))
    done
    exit 0
}

trap cleanup SIGTERM SIGINT


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

    # If a previous SQL error was flagged (persisted in named volume), keep showing error page
    if [ -f "$flag_sql_error" ]; then
        debug "SQL error flag detected from a previous run. Container will start with error page only."
        setup_error_page
        manage_tomcat_lifecycle \
            "Container is running with error page. Fix the SQL issue and remove the flag ($flag_sql_error) to recover."
        return
    fi

    if is_init_done; then
        debug "Container: already configured. Skip DB load and keeping other changes"
    else
        debug "Container: clean. Copying tomcat files and dhis folders"
        copy_apps
        copy_documents
        copy_datavalues
        debug "Container: clean. Load DB"
        wait_for_postgres
        if ! run_sql_files; then
            debug "SQL error detected. Container will start with error page only."
            manage_tomcat_lifecycle \
                "Fix the SQL issue and remove the flag ($flag_sql_error) to recover."
            return
        fi
        run_pre_scripts || true
        init_done
    fi

    post_start_actions() {
        wait_for_tomcat
        run_post_scripts || true
    }

    manage_tomcat_lifecycle \
        "DHIS2 instance ready" \
        post_start_actions
}

env
run "db" "5432"
