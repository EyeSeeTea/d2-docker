#!/bin/bash
#
# Taken from https://github.com/dhis2/dhis2-core/blob/master/docker-entrypoint.sh.
#
# We need our custom entrypoint to perform the following extra tasks:
#  - Make files in TOMCATDIR group-writable (so we can change tomcat files in pre/post scripts)
#  - Install some dependencies: curl, postgresql-client
#
SHELL=/bin/bash
set -e -u

WARFILE=/usr/local/tomcat/webapps/ROOT.war
TOMCATDIR=/usr/local/tomcat/
DHIS2HOME=/DHIS2_home
PACKAGES="curl postgresql-client"

debug() {
    echo "[dhis2-core-start] $*" >&2
}


# Custom
install_packages() {
    if test "$(apk list -I $PACKAGES | wc -l)" -ne 2; then
        # Previous core images did not have package pre-installed, install from static files
        echo "Packages not found, installing"
        #apk add --no-network /config/apk/*.apk
    else
        echo "Packages found"
    fi
}

if [ "$(id -u)" = "0" ]; then
    #install_packages
    if [ -f $WARFILE ]; then
        # Custom: mkdir + add -q to avoid noise in the console
        mkdir -p $TOMCATDIR/webapps/ROOT
        /usr/bin/unzip -n -q $WARFILE -d $TOMCATDIR/webapps/ROOT
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
        su -s /bin/bash tomcat  "$0" "$@"
    fi
fi

exec "$@"
