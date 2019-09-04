#!/bin/bash
#
# Tasks:
#
#   - Wait for the postgres database to be up
#   - Run pre-tomcat scripts
#   - Start Tomcat Catalina
#   - Run post-tomcat scripts
#
set -e -u

dhis2_url="http://localhost:8080"
scripts_dir="/DHIS2_home/scripts"

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

run() { local host=$1 psql_port=$2
    echo "Waiting for postgres: ${host}:${psql_port}"
    while ! nc -z $host $psql_port; do
        sleep 1
    done
    
    run_pre_scripts
    
    echo "Start Tomcat catalina"
    catalina.sh run &
    
    echo "Waiting for Tomcat to start: $dhis2_url"
    while ! curl -sS -i "$dhis2_url" | grep "Location: .*redirect.action" ; do
        sleep 1;
    done
    
    run_post_scripts
    
    wait
}

run "db" "5432"
