#!/bin/sh
# Start OpenResty with workers running as the host user that ran d2-docker (GATEWAY_UID/GATEWAY_GID),
# so request logs written into the mounted host directory are owned by that user. Default: nobody.
set -e -u

uid=${GATEWAY_UID:-65534}
gid=${GATEWAY_GID:-65534}

if [ "$uid" = 0 ]; then
    user=root
    group=root
else
    group=$(getent group "$gid" | cut -d: -f1)
    if [ -z "$group" ]; then
        addgroup -g "$gid" d2docker
        group=d2docker
    fi

    user=$(getent passwd "$uid" | cut -d: -f1)
    if [ -z "$user" ]; then
        adduser -D -H -u "$uid" -G "$group" -s /sbin/nologin d2docker
        user=d2docker
    fi
fi

exec /usr/local/openresty/bin/openresty -g "daemon off; user $user $group;"
