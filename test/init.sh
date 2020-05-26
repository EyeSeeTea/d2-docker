#!/bin/bash
set -e -u -o pipefail

wget -nc "https://releases.dhis2.org/2.30/dhis.war"
wget -nc "https://github.com/dhis2/dhis2-demo-db/raw/master/sierra-leone/2.30/dhis2-db-sierra-leone.sql.gz"

mkdir -p upgrade-migrations/2.31

(cd upgrade-migrations/2.31 && wget -nc https://releases.dhis2.org/2.31/2.31.8/dhis.war)
