#!/bin/bash -x -e -u -o pipefail

wait_for_dhis2() {
    echo "Wait for Dhis2 instance"
    while ! curl -u admin:district -sS http://localhost:8080/api/me.json 2>/dev/null | jq 2>/dev/null; do
        sleep 1;
    done
}

expect_equal() { local actual=$1 expected=$2
    if test "$actual" != "$expected"; then
        echo "Error:"
        echo " expected = $expected"
        echo " action = $actual"
        return 1;
    fi
}

wget -c "https://releases.dhis2.org/2.30/dhis.war"
wget -c "https://github.com/dhis2/dhis2-demo-db/raw/master/sierra-leone/dev/dhis2-db-sierra-leone.sql.gz"
mkdir -p apps/
echo "select * from users;" > get-users.sql
echo "update userinfo set firstname = 'John2' where uid = 'xE7jOejl9FI';" > set-name.sql

d2-docker create core tokland/dhis2-core:2.30 --war=dhis.war
d2-docker create data tokland/dhis2-data:2.30-sierra \
--sql=dhis2-db-sierra-leone.sql.gz --apps-dir=apps/
d2-docker list
d2-docker start -d tokland/dhis2-data:2.30-sierra
wait_for_dhis2

d2-docker list | grep "tokland/dhis2-data:2.30-sierra" | grep "RUNNING\[port=8080\]"
d2-docker logs
name=$(curl -sS -u admin:district 'http://localhost:8080/api/me' | jq -r '.displayName')
expect_equal "$name" "John Traore"
d2-docker run-sql -i tokland/dhis2-data:2.30-sierra get-users.sql
d2-docker commit
#d2-docker push # too slow
d2-docker export image.tgz

d2-docker stop tokland/dhis2-data:2.30-sierra
d2-docker copy tokland/dhis2-data:2.30-sierra data-sierra tokland/dhis2-data:2.30-sierra2
d2-docker copy data-sierra tokland/dhis2-data:2.30-sierra3
d2-docker stop tokland/dhis2-data:2.30-sierra
d2-docker import image.tgz
d2-docker start -d --run-sql=set-name.sql image.tgz
wait_for_dhis2

name=$(curl -sS -u admin:district 'http://localhost:8080/api/me' | jq -r '.displayName')
expect_equal "$name" "John2 Traore"
d2-docker stop tokland/dhis2-data:2.30-sierra

echo "Tests passed!"
