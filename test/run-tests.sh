#!/bin/bash
set -e -u -o pipefail

wait_for_dhis2() {
    echo "Wait for Dhis2 instance"
    while ! curl -u admin:district -sS http://localhost:8080/api/me.json 2>/dev/null | jq 2>/dev/null; do
        sleep 10
    done
}

expect_equal() {
    local actual=$1 expected=$2
    if test "$actual" != "$expected"; then
        echo "Error:"
        echo " expected = $expected"
        echo " actual = $actual"
        return 1
    fi
}

mkdir -p apps/ sql/
echo "select * from users;" >sql/get-users.sql
echo "update userinfo set firstname = 'John2' where uid = 'xE7jOejl9FI';" >sql/set-name.sql

d2-docker create core tokland/dhis2-core:2.30 --war=dhis.war
d2-docker create data tokland/dhis2-data:2.30-sierra \
    --sql=dhis2-db-sierra-leone.sql.gz --apps-dir=apps/
d2-docker list
d2-docker start -d tokland/dhis2-data:2.30-sierra
wait_for_dhis2

d2-docker list | grep "tokland/dhis2-data:2.30-sierra" | grep "RUNNING"
d2-docker logs tokland/dhis2-data:2.30-sierra
name=$(curl -sS -u admin:district 'http://localhost:8080/api/me' | jq -r '.displayName')
expect_equal "$name" "John Traore"
d2-docker run-sql -i tokland/dhis2-data:2.30-sierra sql/get-users.sql
d2-docker commit tokland/dhis2-data:2.30-sierra
d2-docker export image.tgz

d2-docker stop tokland/dhis2-data:2.30-sierra
d2-docker copy tokland/dhis2-data:2.30-sierra data-sierra tokland/dhis2-data:2.30-sierra2
d2-docker import image.tgz
d2-docker start -d --run-sql=sql image.tgz
wait_for_dhis2

name=$(curl -sS -u admin:district 'http://localhost:8080/api/me' | jq -r '.displayName')
expect_equal "$name" "John2 Traore"
d2-docker stop tokland/dhis2-data:2.30-sierra

d2-docker upgrade \
    --from=tokland/dhis2-data:2.30-sierra \
    --to=tokland/dhis2-data:2.31-sierra \
    --migrations=upgrade-migrations

d2-docker rm tokland/dhis2-data:2.31-sierra
d2-docker rm tokland/dhis2-data:2.30-sierra

echo "Tests passed!"
