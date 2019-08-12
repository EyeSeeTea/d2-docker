#!/bin/bash
set -e -u

run() {
    local host="db"
    local psql_port="5432"
    
    echo "Waiting for postgres ${host}:${psql_port}"
    while ! nc -z $host $psql_port; do
        sleep 0.1
    done
    
    echo "Start catalina"
    catalina.sh run
}

run
