import argparse
import re
import shlex

from d2_docker import utils
from d2_docker.commands import start

DESCRIPTION = "Migrate the DB of a running instance to another PostgreSQL major (into a new image)"
NAME = "migrate-db"

# Tables that DHIS2 may legitimately clean up on startup
VOLATILE_TABLES_RE = r"^(spring_session.*|.*session.*|oauth2_.*|audit.*|deletedobject|jobconfiguration)$"

TABLE_COUNTS_SQL = """
SELECT table_name, (xpath('/row/c/text()',
    query_to_xml(format('SELECT count(*) AS c FROM public.%I', table_name), false, true, '')))[1]::text
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name NOT LIKE 'analytics%'
ORDER BY table_name
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
        help='Extra "d2-docker start" options for the migrated instance, as one string '
        '(Ex: "--java-opts=-Xmx4g --auth admin:district")',
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only check the instance and show what would be done"
    )


def run(args):
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

    core_image = inspect(containers["core"], "{{.Config.Image}}")
    deploy_path = inspect(containers["gateway"], '{{index .Config.Labels "com.eyeseetea.deploy-path"}}')
    port = args.port or status["port"]
    start_argv = [
        dest,
        "--detach",
        "--core-image", core_image,
        "--port", str(port),
        "--postgis-version", args.postgis_version,
        *(["--deploy-path", deploy_path] if deploy_path else []),
        *shlex.split(args.start_args),
    ]
    rollback = "d2-docker stop {} && d2-docker start {} -k --port {}".format(dest, source, port)

    logger = utils.logger
    logger.info("Migrate DB: {} (PostgreSQL {}) -> {} (postgis/postgis:{})".format(
        source, source_pg_major, dest, args.postgis_version))
    logger.info("  1. Dump DB + files of {} into new image {} (the source image is not modified)".format(
        source, dest))
    logger.info("  2. Stop {} (its containers and volumes are kept, for rollback)".format(source))
    logger.info("  3. d2-docker start {}".format(" ".join(start_argv)))
    logger.info("  4. Compare row counts and files")
    logger.info("Options of the source start (dhis.conf, java opts, auth...) are not stored, "
                "pass them with --start-args")

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
        if not utils.wait_for_server(port):
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

    logger.info("Checked {} tables and {} file folders".format(len(counts_before), len(files_before)))
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


def get_server_pg_major(db_container):
    output = psql(db_container, "SHOW server_version_num").strip()
    return str(int(output) // 10000)


def get_table_counts(db_container):
    logger = utils.logger
    logger.info("Count rows of all tables (except analytics*)")
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


def inspect(container, fmt):
    result = utils.run(["docker", "inspect", "--format", fmt, container], capture_output=True)
    return result.stdout.decode("utf-8").strip()


def image_exists(image):
    result = utils.run(["docker", "image", "inspect", image], capture_output=True, raise_on_error=False)
    return result.returncode == 0
