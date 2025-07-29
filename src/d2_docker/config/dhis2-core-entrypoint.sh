#!/bin/bash
#
# Based on the current latest tagged version of dhis2-core entrypoint:
# https://github.com/dhis2/dhis2-core/blob/2.36.11.1/docker/tomcat-debian/docker-entrypoint.sh
#
# We need our custom entrypoint to perform the following different tasks:
#  - Make files in TOMCATDIR be of user tomcat (so we can change tomcat files in pre/post scripts)
#
set -e # exit on errors

WARFILE=/usr/local/tomcat/webapps/ROOT.war
TOMCATDIR=/usr/local/tomcat
DHIS2HOME=/DHIS2_home
DATA_DIR=/data
GLOWROOT_ZIP="/opt/glowroot.zip"
GLOWROOT_DIR="/opt/glowroot"


debug() {
    echo "[dhis2-core-entrypoint] $*" >&2
}

curl_status_connection_refused=7

wait_for_data_container_to_finish_copy() {
    # We must wait for the data container before starting Tomcat. As ping is not installed
    # in the image, use curl instead.
    local statuscode

    while true; do
        statuscode=0
        curl -sS --connect-timeout 1 data || statuscode=$?

        case $statuscode in
        "$curl_status_connection_refused")
            debug "data container is still running, wait"
            sleep 2
            continue
            ;;
        *)
            debug "data container has finished, continue"
            break
            ;;
        esac
    done

}

setup_glowroot() {
    if [ -f $GLOWROOT_ZIP ] && [ ! -d $GLOWROOT_DIR ] ; then
        status=0
        unzip -q "$GLOWROOT_ZIP" -d /opt/ || status=$?
        # Ignore RC=1 that implies only warnings and no errors (like an empty zip file)
        if [ $status -gt 1 ]; then
            exit $status
        fi
        if [ -d $GLOWROOT_DIR ] ; then
            echo '{ "web": { "bindAddress": "0.0.0.0", "port": "4000" }}' > $GLOWROOT_DIR/admin.json
            chown -R tomcat:tomcat $GLOWROOT_DIR
            chmod -R u=rwX,g=rX,o-rwx $GLOWROOT_DIR
            echo 'export CATALINA_OPTS="$CATALINA_OPTS -javaagent:/opt/glowroot/glowroot.jar"' > /usr/local/tomcat/bin/setenv.sh
            chmod ugo+x /usr/local/tomcat/bin/setenv.sh
            chown tomcat:tomcat /usr/local/tomcat/bin/setenv.sh
        fi
    fi
}

if [ "$(id -u)" = "0" ]; then
    if [ -f $WARFILE ]; then
        unzip -q $WARFILE -d $TOMCATDIR/webapps/ROOT
        rm -v $WARFILE # just to save space
    fi

    setup_glowroot
    wait_for_data_container_to_finish_copy

    mkdir -p $DATA_DIR/apps
    chown -R tomcat:tomcat $TOMCATDIR $DATA_DIR/apps $DHIS2HOME
    chmod -R u=rwX,g=rX,o-rwx $TOMCATDIR $DATA_DIR/apps $DHIS2HOME

    # Launch the given command as tomcat, in two ways for backwards compatibility:
    if [ "$(grep '^ID=' /etc/os-release)" = "ID=alpine" ]; then
        # The alpine linux way (for old images).
        exec su-exec tomcat "$0" "$@"
    else
        # The ubuntu way (for new images).
        exec setpriv --reuid=tomcat --regid=tomcat --init-groups "$0" "$@"
    fi
fi

exec "$@"
