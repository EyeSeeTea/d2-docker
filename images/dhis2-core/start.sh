#!/bin/bash
#
# Wait for the postgres database to be UP before running tomcat.
#
set -e -u

run() { local host=$1 psql_port=$2
    echo "Waiting for postgres ${host}:${psql_port}"
    while ! nc -z $host $psql_port; do
        sleep 1
    done
    
    echo "Start Tomcat catalina"
    catalina.sh run
}

run "db" "5432"
