import os
import subprocess
from d2_docker import utils

DESCRIPTION = "Run SQL or open interactive session in a d2-docker container"
NAME = "run-sql"


def setup(parser):
    utils.add_image_arg(parser)
    parser.add_argument(
        "sql_file",
        metavar="SQL_FILE",
        nargs="?",
        help="SQL file (if empty, open interactive psql terminal)",
    )
    parser.add_argument("--dump", action="store_true", help="Dump SQL")


def run_sql_file(sql_file, db_container, image_name):
    utils.logger.info("Run SQL file {} for image {}".format(sql_file, image_name))
    psql_cmd = ["psql", "-U", "dhis", "dhis2"]
    cmd = ["docker", "exec", ("-i" if sql_file else "-it"), db_container, *psql_cmd]
    stdin = open(sql_file, encoding="utf-8") if sql_file else None
    result = utils.run(cmd, stdin=stdin, raise_on_error=False)
    
    if result.returncode != 0:
        utils.logger.error("Could not execute SQL")
        return 1


def run(args):
    image_name = args.image or utils.get_running_image_name()
    sql_file = args.sql_file

    status = utils.get_image_status(image_name)
    is_running = status["state"] == "running"
    running_containers = utils.noop(status) if is_running else utils.running_containers

    with running_containers(image_name, "db") as status:
        db_container = status["containers"]["db"]
        utils.logger.debug("DB container: {}".format(db_container))

        if args.dump:
            cmd = ["docker", "exec", db_container, "pg_dump", "-U", "dhis", "dhis2"]
            utils.logger.info("Dump SQL for image {}".format(image_name))
            utils.run(cmd, raise_on_error=False)
        else:
            utils.logger.info("Run SQL for image {}".format(image_name))
            if sql_file is not None and os.path.isdir(sql_file):
                sql_files = [os.path.join(sql_file, f) for f in os.listdir(sql_file) if f.endswith(".sql")]
                for sql_file in sql_files:
                    run_sql_file(sql_file, db_container, image_name)
            else:
                run_sql_file(sql_file, db_container, image_name)


def get_stream_db(image):
    image_name = image or utils.get_running_image_name()
    status = utils.get_image_status(image_name)

    if status["state"] != "running":
        raise utils.D2DockerError("Container must be running to dump database")

    db_container = status["containers"]["db"]
    cmd_parts = ["docker", "exec", db_container, "pg_dump", "-U", "dhis", "dhis2", "|", "gzip"]
    cmd = subprocess.list2cmdline(cmd_parts)
    utils.logger.info("Dump SQL for image: {}".format(cmd))

    popen = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,  # nosec
    )

    return utils.stream_binary_from_popen(popen)
