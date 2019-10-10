#!/bin/sh
#
# Taken from https://github.com/dhis2/dhis2-core/blob/master/docker-entrypoint.sh.
#
# We need our custom entrypoint to perform the following extra tasks:
#  - Make files in TOMCATDIR group-writable (so we can change tomcat files in pre/post scripts)
#  - Install some dependencies: curl, postgresql-client
#
set -e -u -o pipefail

WARFILE=/usr/local/tomcat/webapps/ROOT.war
TOMCATDIR=/usr/local/tomcat
DHIS2HOME=/DHIS2_home
PACKAGES="curl postgresql-client"

# Custom
install_packages() {
    apk add --no-network /config/apk/*.apk
}

if [ "$(id -u)" = "0" ]; then
    # Custom
    install_packages $PACKAGES
    
    if [ -f $WARFILE ]; then
        # Custom: mkdir + add -q to avoid noise in the console
        mkdir -p $TOMCATDIR/webapps/ROOT
        unzip -n -q $WARFILE -d $TOMCATDIR/webapps/ROOT
        rm $WARFILE
    fi
    
    # dhis2/core 2.31 images do not have user tomcat, don't fail in this case
    
    if getent group tomcat; then
        chown -R root:tomcat $TOMCATDIR
        # Custom. Before: u+rwX,g+rX,o-rwx
        chmod -R u+rwX,g+rwX,o-rwx $TOMCATDIR
        chown -R tomcat:tomcat $TOMCATDIR/temp \
        $TOMCATDIR/work \
        $TOMCATDIR/logs
        chown -R tomcat:tomcat $DHIS2HOME
        chmod +x "$0" || true
        exec su-exec tomcat "$0" "$@"
    fi
fi

exec "$@"
