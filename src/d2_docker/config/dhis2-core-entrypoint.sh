#!/bin/bash
#
# Based on the current latest tagged version of dhis2-core entrypoint:
# https://github.com/dhis2/dhis2-core/blob/2.36.11.1/docker/tomcat-debian/docker-entrypoint.sh
#
# We need our custom entrypoint to perform the following different tasks:
#  - Make files in TOMCATDIR be of user tomcat (so we can change tomcat files in pre/post scripts)
#
set -e  # exit on errors

WARFILE=/usr/local/tomcat/webapps/ROOT.war
TOMCATDIR=/usr/local/tomcat
DHIS2HOME=/DHIS2_home
DATA_DIR=/data

if [ "$(id -u)" = "0" ]; then
    if [ -f $WARFILE ]; then
        unzip -q $WARFILE -d $TOMCATDIR/webapps/ROOT
        rm -v $WARFILE  # just to save space
    fi

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
