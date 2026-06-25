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
APPROOT=$TOMCATDIR/webapps/ROOT

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
        output=$(unzip -q "$GLOWROOT_ZIP" -d /opt/ 2>&1) || status=$?
        # Ignore RC=1 that implies only warnings and no errors (like an empty zip file)
        if [ $status -gt 1 ]; then
            echo "$output"
            exit $status
        fi
        if [ -d $GLOWROOT_DIR ] ; then
            echo '{ "web": { "bindAddress": "0.0.0.0", "port": "4000" }}' > $GLOWROOT_DIR/admin.json
            echo '{"transactions":{"slowThresholdMillis":2000,"profilingIntervalMillis":1000,"captureThreadStats":true},
        "jvm":{"maskSystemProperties":["*password*","*token*","*access*","*secret*"],"maskMBeanAttributes":["*password*","*token*","*access*","*secret*"]},
        "uiDefaults":{"defaultTransactionType":"Web","defaultPercentiles":[50,95,99],"defaultGaugeNames":["java.lang:type=Memory:HeapMemoryUsage.used"]},
        "advanced":{"immediatePartialStoreThresholdSeconds":60,"maxTransactionAggregates":500,"maxQueryAggregates":500,"maxServiceCallAggregates":500,
        "maxTraceEntriesPerTransaction":2000,"maxProfileSamplesPerTransaction":50000,"mbeanGaugeNotFoundDelaySeconds":60},"gauges":[{"mbeanObjectName":"java.lang:type=Memory",
        "mbeanAttributes":[{"name":"HeapMemoryUsage.used"}]},{"mbeanObjectName":"java.lang:type=GarbageCollector,name=*","mbeanAttributes":[{"name":"CollectionCount","counter":true},
        {"name":"CollectionTime","counter":true}]},{"mbeanObjectName":"java.lang:type=MemoryPool,name=*","mbeanAttributes":[{"name":"Usage.used"}]},
        {"mbeanObjectName":"java.lang:type=OperatingSystem","mbeanAttributes":[{"name":"FreePhysicalMemorySize"},{"name":"ProcessCpuLoad"},{"name":"SystemCpuLoad"}]}],
        "plugins":[{"properties":{"stackTraceThresholdMillis":1000},"id":"cassandra"},{"properties":{"stackTraceThresholdMillis":1000},"id":"elasticsearch"},
        {"properties":{"sessionUserAttribute":"","captureSessionAttributes":[],"captureRequestParameters":["*"],"maskRequestParameters":["*password*","*token*","*access*","*secret*"],
        "captureRequestHeaders":[],"captureResponseHeaders":[],"traceErrorOn4xxResponseCode":false,"captureRequestRemoteAddr":false,"captureRequestRemoteHostname":false,
        "captureRequestRemotePort":false,"captureRequestLocalAddr":false,"captureRequestLocalHostname":false,"captureRequestLocalPort":false,"captureRequestServerHostname":false,
        "captureRequestServerPort":false},"id":"jakartaservlet"},{"properties":{"captureRequestHeaders":[],"maskRequestHeaders":["Authorization"],"captureRequestRemoteAddr":false,
        "captureRequestRemoteHost":false,"captureResponseHeaders":[],"traceErrorOn4xxResponseCode":false},"id":"java-http-server"},{"properties":{"useAltTransactionNaming":false},
        "id":"jaxrs"},{"properties":{"captureBindParametersIncludes":[".*"],"captureBindParametersExcludes":[],"captureResultSetNavigate":true,"captureResultSetGet":false,
        "captureConnectionPoolLeaks":false,"captureConnectionPoolLeakDetails":false,"captureGetConnection":true,"captureConnectionClose":false,"capturePreparedStatementCreation":false,
        "captureStatementClose":false,"captureTransactionLifecycleTraceEntries":false,"captureConnectionLifecycleTraceEntries":false,"stackTraceThresholdMillis":1000},"id":"jdbc"},
        {"properties":{"traceErrorOnErrorWithThrowable":true,"traceErrorOnErrorWithoutThrowable":false,"traceErrorOnWarningWithThrowable":false,"traceErrorOnWarningWithoutThrowable":false},
        "id":"logger"},{"properties":{"stackTraceThresholdMillis":1000},"id":"mongodb"},{"properties":{"useAltTransactionNaming":false},"id":"play"},{"properties":{"sessionUserAttribute":"",
        "captureSessionAttributes":[],"captureRequestParameters":["*"],"maskRequestParameters":["*password*","*token*","*access*","*secret*"],"captureRequestHeaders":[],
        "captureResponseHeaders":[],"traceErrorOn4xxResponseCode":false,"captureRequestRemoteAddr":false,"captureRequestRemoteHostname":false,"captureRequestRemotePort":false,
        "captureRequestLocalAddr":false,"captureRequestLocalHostname":false,"captureRequestLocalPort":false,"captureRequestServerHostname":false,"captureRequestServerPort":false},
        "id":"servlet"},{"properties":{"useAltTransactionNaming":false},"id":"spring"}],"instrumentation":[{"className":"org.hisp.dhis.webapi.controller.event.TrackedEntityInstanceController",
        "methodName":"getTrackedEntityInstances","methodParameterTypes":[".."],"order":0,"captureKind":"other","transactionType":"Web","transactionNameTemplate":"/api/trackedEntityInstances: GET"},
        {"className":"org.hisp.dhis.tracker.report.DefaultTrackerImportService","methodName":"importTracker","methodParameterTypes":[".."],"order":0,"captureKind":"transaction",
        "transactionType":"Web","transactionNameTemplate":"/api/tracker: import","alreadyInTransactionBehavior":"capture-new-transaction","traceEntryMessageTemplate":"{{0}}",
        "traceEntryStackThresholdMillis":300,"traceEntryCaptureSelfNested":true,"timerName":"Timer"}]}' > $GLOWROOT_DIR/config.json
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
        unzip -q $WARFILE -d $APPROOT
        rm -v $WARFILE  # just to save space
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
