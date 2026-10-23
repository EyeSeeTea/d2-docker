import argparse
import json
import os
import re
import shlex

from d2_docker import utils
from d2_docker.commands import start

DESCRIPTION = "Migrate the DB of a running instance to another PostgreSQL major (into a new image)"
NAME = "migrate-db"

DEFAULT_JAVA_OPTS = "-Xmx7500m -Xms4000m"
DEFAULT_WAIT_TIMEOUT_MINUTES = 30

# Tables that DHIS2 may legitimately clean up on startup
VOLATILE_TABLES_RE = r"^(spring_session.*|.*session.*|oauth2_.*|audit.*|deletedobject|jobconfiguration)$"

# Row count of every table (analytics tables are not dumped) plus the number of schema
# objects ("~name" rows), excluding the ones owned by extensions (PostGIS).
TABLE_COUNTS_SQL = """
WITH ext AS (SELECT classid, objid FROM pg_depend WHERE deptype = 'e'),
rels AS (
    SELECT c.oid, c.relname, c.relkind FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname NOT LIKE 'analytics%'
    AND NOT EXISTS (SELECT 1 FROM ext WHERE classid = 'pg_class'::regclass AND objid = c.oid)
)
SELECT relname, (xpath('/row/c/text()',
    query_to_xml(format('SELECT count(*) AS c FROM public.%I', relname), false, true, '')))[1]::text
FROM rels WHERE relkind IN ('r', 'p')
UNION ALL SELECT '~indexes', count(*)::text FROM pg_index i JOIN rels t ON t.oid = i.indrelid
UNION ALL SELECT '~constraints', count(*)::text FROM pg_constraint c JOIN rels t ON t.oid = c.conrelid
UNION ALL SELECT '~views', count(*)::text FROM rels WHERE relkind IN ('v', 'm')
UNION ALL SELECT '~sequences', count(*)::text FROM rels WHERE relkind = 'S'
UNION ALL SELECT '~functions', count(*)::text FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public'
    AND NOT EXISTS (SELECT 1 FROM ext WHERE classid = 'pg_proc'::regclass AND objid = p.oid)
ORDER BY 1
"""

FILES_SUMMARY_CMD = (
    "cd /DHIS2_home/files 2>/dev/null || exit 0; "
    "for d in */; do echo \"${d%/} $(find \"$d\" -type f | wc -l)\"; done"
)


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", help="Running d2-docker data image to migrate")
    parser.add_argument(
        "--postgis-version",
        default="16-3.5-alpine",
        help="Destination postgis/postgis image version (default: 16-3.5-alpine)",
    )
    parser.add_argument(
        "--dest", metavar="IMAGE", help="Destination data image (default: IMAGE-pg<MAJOR>)"
    )
    parser.add_argument(
        "-p", "--port", type=int, metavar="N", help="Port for the migrated instance (default: same)"
    )
    parser.add_argument(
        "--start-args",
        default="",
        metavar="ARGS",
        help='Extra "d2-docker start" options for the migrated instance, as one string. '
        "Options of the running instance (bind IP, java opts, auth, dhis.conf, server.xml, "
        "debug/db ports, deploy path) are reused automatically",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=DEFAULT_WAIT_TIMEOUT_MINUTES,
        metavar="MINUTES",
        help="Max time for the migrated instance to load the dump and start (default: {})".format(
            DEFAULT_WAIT_TIMEOUT_MINUTES
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only check the instance and show what would be done"
    )


def run(args):
    logger = utils.logger
    source = args.image
    status = utils.get_image_status(source)
    if status["state"] != "running":
        msg = "Instance must be running to dump its DB: d2-docker start {} -k".format(source)
        raise utils.D2DockerError(msg)

    containers = status["containers"]
    target_pg_major = utils.get_pg_major_from_postgis_version(args.postgis_version)
    source_pg_major = get_server_pg_major(containers["db"])
    if not target_pg_major:
        raise utils.D2DockerError("Invalid --postgis-version: {}".format(args.postgis_version))
    if source_pg_major == target_pg_major:
        msg = "Instance {} is already on PostgreSQL {}".format(source, source_pg_major)
        raise utils.D2DockerError(msg)

    dest = args.dest or "{}-pg{}".format(source, target_pg_major)
    if image_exists(dest):
        msg = "Destination image {} already exists, use --dest or d2-docker rm".format(dest)
        raise utils.D2DockerError(msg)

    infos = dict((service, inspect(container)) for service, container in containers.items())
    check_db_volume_is_internal(infos["db"])
    source_args, deploy_path = get_source_start_args(infos)
    port = args.port or status["port"]
    core_image = infos["core"]["Config"]["Image"]
    common_args = ["--core-image", core_image, "--port", str(port), *source_args]
    start_argv = [
        dest,
        "--detach",
        *common_args,
        "--postgis-version", args.postgis_version,
        *shlex.split(args.start_args),
    ]
    rollback = "d2-docker stop {} && d2-docker start {} -k --detach {}".format(
        dest, source, " ".join(shlex.quote(arg) for arg in common_args)
    )

    dhis2_major = utils.get_major_version(source.rsplit(":", 1)[-1])
    if int(target_pg_major.split(".")[0]) >= 16 and dhis2_major and dhis2_major < 41:
        logger.warning("DHIS2 {} recommends PostgreSQL 14/15, not {}".format(dhis2_major, target_pg_major))

    logger.info("Migrate DB: {} (PostgreSQL {}, {}) -> {} (postgis/postgis:{})".format(
        source, source_pg_major, get_db_size(containers["db"]), dest, args.postgis_version))
    logger.info("  1. Dump DB + files of {} into new image {} (the source image is not modified)".format(
        source, dest))
    logger.info("  2. Stop {} (its containers and volumes are kept, for rollback)".format(source))
    logger.info("  3. d2-docker start {}".format(" ".join(shlex.quote(arg) for arg in start_argv)))
    logger.info("  4. Compare row counts, schema objects and files")
    logger.info("Changes made in {} after the dump are not migrated: plan a downtime".format(source))

    if args.dry_run:
        logger.info("Dry run, nothing done. Rollback after a real run: {}".format(rollback))
        return

    counts_before = get_table_counts(containers["db"])
    files_before = get_files_summary(containers["core"])
    check_folders_included(files_before)

    docker_dir = utils.get_docker_directory("data", args)
    temp_dir = utils.get_temp_base_directory(args)
    utils.build_image_from_source(docker_dir, source, dest, temp_dir)

    logger.info("Stop source instance: {}".format(source))
    utils.run_docker_compose(["stop"], source)

    try:
        start_parser = argparse.ArgumentParser(prog="d2-docker start")
        start.setup(start_parser)
        start.run(start_parser.parse_args(start_argv))
        if not utils.wait_for_server(port, timeout=args.wait_timeout * 60, path=deploy_path):
            raise utils.D2DockerError("Error waiting for DHIS2 instance {}".format(dest))
    except BaseException:
        logger.error("Migration failed. Rollback: {}".format(rollback))
        raise

    dest_containers = utils.get_image_status(dest)["containers"]
    dest_pg_major = get_server_pg_major(dest_containers["db"])
    counts_after = get_table_counts(dest_containers["db"])
    files_after = get_files_summary(dest_containers["core"])

    errors = compare(counts_before, counts_after, "rows in table", VOLATILE_TABLES_RE)
    errors += compare(files_before, files_after, "files in DHIS2_home/files", None)
    if dest_pg_major != target_pg_major:
        errors.append("Destination is PostgreSQL {}, expected {}".format(dest_pg_major, target_pg_major))

    logger.info("Checked {} tables/objects and {} file folders".format(
        len(counts_before), len(files_before)))
    if errors:
        for error in errors:
            logger.error(error)
        msg = "Migration finished with differences, check them. Rollback: {}".format(rollback)
        raise utils.D2DockerError(msg)

    logger.info("Migration OK: {} running on PostgreSQL {} (port {})".format(dest, dest_pg_major, port))
    logger.info("Next steps:")
    logger.info("  - Check the instance and regenerate analytics tables (they are not dumped)")
    logger.info("  - Rollback: {}".format(rollback))
    logger.info("  - When validated, remove the source: d2-docker rm {} (and its volumes)".format(source))


def get_source_start_args(infos):
    """Return the "d2-docker start" options of the running instance, and its deploy path."""
    logger = utils.logger
    core, gateway, db = infos["core"], infos["gateway"], infos["db"]
    env = dict(entry.split("=", 1) for entry in core["Config"]["Env"] if "=" in entry)
    mounts = dict((mount["Destination"], mount.get("Source")) for mount in core["Mounts"])
    # Use --option=value: argparse rejects values starting with "-" (Ex: java opts)
    args = []

    bind_ip = get_host_binding(gateway, "80/tcp")[0]
    if bind_ip and bind_ip != "0.0.0.0":
        args += ["--bind-ip=" + bind_ip]

    deploy_path = env.get("DEPLOY_PATH", "")
    if deploy_path:
        args += ["--deploy-path=" + deploy_path]

    java_opts = env.get("JAVA_OPTS", "").replace(DEFAULT_JAVA_OPTS, "", 1).strip()
    if java_opts:
        args += ["--java-opts=" + java_opts]

    if env.get("DHIS2_AUTH"):
        args += ["--auth=" + env["DHIS2_AUTH"]]

    for destination, option in [
        ("/config/override/dhis2/dhis.conf", "--dhis-conf"),
        ("/config/override/tomcat/server.xml", "--tomcat-server-xml"),
    ]:
        source = mounts.get(destination)
        if source and os.path.isfile(source) and os.path.getsize(source) > 0:
            args += [option + "=" + source]

    for host_port_option, (info, container_port) in [
        ("--debug-port", (core, "8000/tcp")),
        ("--db-port", (db, "5432/tcp")),
    ]:
        ip, host_port = get_host_binding(info, container_port)
        if host_port:
            args += ["{}={}:{}".format(host_port_option, ip or "0.0.0.0", host_port)]

    if get_host_binding(core, "4000/tcp")[1]:
        logger.warning("Glowroot is enabled in the source, pass --start-args=--glowroot-port=...")

    if "logging_collector=on" in " ".join(db["Config"]["Cmd"] or []):
        args += ["--enable-postgres-queries-logging"]

    for destination, option in [("/data/db/post", "--run-sql"), ("/data/scripts", "--run-scripts")]:
        source = mounts.get(destination)
        if source and not source.rstrip("/").endswith(".empty"):
            logger.warning("Source was started with {} {}: not reused".format(option, source))

    return args, ("/" + deploy_path.lstrip("/") if deploy_path else "")


def get_host_binding(info, container_port):
    bindings = (info["HostConfig"].get("PortBindings") or {}).get(container_port) or []
    if not bindings:
        return (None, None)
    return (bindings[0].get("HostIp") or None, bindings[0].get("HostPort") or None)


def check_db_volume_is_internal(db_info):
    for mount in db_info["Mounts"]:
        if mount["Destination"] == "/var/lib/postgresql/data" and mount["Type"] == "volume":
            volume = inspect_volume(mount["Name"])
            if (volume.get("Options") or {}).get("device"):
                msg = "Instances with --external-db-volume are not supported by migrate-db"
                raise utils.D2DockerError(msg)


def get_server_pg_major(db_container):
    version_num = int(psql(db_container, "SHOW server_version_num").strip())
    # Since PostgreSQL 10 the major is one number (160015 -> 16), before it was two (90624 -> 9.6)
    major = version_num // 10000
    return str(major) if major >= 10 else "{}.{}".format(major, version_num // 100 % 100)


def get_db_size(db_container):
    return psql(db_container, "SELECT pg_size_pretty(pg_database_size('dhis2'))").strip()


def get_table_counts(db_container):
    utils.logger.info("Count rows of all tables (except analytics*) and schema objects")
    lines = psql(db_container, TABLE_COUNTS_SQL).splitlines()
    return dict((name, int(count)) for name, count in (line.split("|") for line in lines if line))


def get_files_summary(core_container):
    result = utils.run(
        ["docker", "exec", core_container, "sh", "-c", FILES_SUMMARY_CMD], capture_output=True
    )
    lines = result.stdout.decode("utf-8").splitlines()
    return dict((name, int(count)) for name, count in (line.rsplit(" ", 1) for line in lines if line))


def check_folders_included(files_summary):
    for folder, count in files_summary.items():
        if folder not in utils.default_folders and count:
            utils.logger.warning(
                "Folder files/{} ({} files) is not included in the dump".format(folder, count)
            )


def compare(before, after, description, ignore_re):
    errors = []
    for key, count_before in before.items():
        count_after = after.get(key, 0)
        if count_after < count_before:
            msg = "{} {}: {} -> {}".format(description, key, count_before, count_after)
            if ignore_re and re.match(ignore_re, key):
                utils.logger.warning(msg + " (ignored, cleaned up by DHIS2)")
            elif description.startswith("files") and key not in utils.default_folders:
                utils.logger.warning(msg + " (folder not included in the dump)")
            else:
                errors.append(msg)
    return errors


def psql(db_container, sql):
    cmd = ["docker", "exec", db_container, "psql", "-U", "dhis", "-d", "dhis2", "-tA", "-c", sql]
    return utils.run(cmd, capture_output=True).stdout.decode("utf-8")


def inspect(container):
    result = utils.run(["docker", "inspect", container], capture_output=True)
    return json.loads(result.stdout.decode("utf-8"))[0]


def inspect_volume(volume):
    result = utils.run(["docker", "volume", "inspect", volume], capture_output=True)
    return json.loads(result.stdout.decode("utf-8"))[0]


def image_exists(image):
    result = utils.run(["docker", "image", "inspect", image], capture_output=True, raise_on_error=False)
    return result.returncode == 0
