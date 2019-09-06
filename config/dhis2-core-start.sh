#!/bin/bash
set -e -u -o pipefail
#
# Tasks:
#
#   - Install dependencies
#   - Wait for the postgres database to be up
#   - Run pre-tomcat scripts
#   - Start Tomcat Catalina
#   - Run post-tomcat scripts
#

dhis2_url="http://localhost:8080"
scripts_dir="/DHIS2_home/scripts"
source_apps_path="/DHIS2_home/data/apps"
dest_apps_path="/DHIS2_home/files/"

run_pre_scripts() {
    find "$scripts_dir" -type f -name '*.sh' ! \( -name 'post*' \) | sort | while read path; do
        echo "Run pre-tomcat script: $path"
        bash "$path"
    done
}

run_post_scripts() {
    find "$scripts_dir" -type f -name '*.sh' -name 'post*' | sort | while read path; do
        echo "Run post-tomcat script: $path"
        bash "$path"
    done
}


copy_apps() {
    echo "Copy Dhis2 apps"
    mkdir -p "$dest_apps_path/apps"
    if test -e "$source_apps_path"; then
        cp -av "$source_apps_path" "$dest_apps_path"
    fi
}

run() { host=$1 psql_port=$2
    copy_apps
    
    echo "Waiting for postgres: ${host}:${psql_port}"
    while ! nc -z $host $psql_port; do
        sleep 1
    done
    
    run_pre_scripts || true
    
    echo "Start Tomcat catalina"
    catalina.sh run &
    
    echo "Waiting for Tomcat to start: $dhis2_url"
    while ! curl -sS -i "$dhis2_url" | grep "Location: .*redirect.action" ; do
        sleep 1;
    done
    
    run_post_scripts  || true
    
    wait
}

run "db" "5432"
