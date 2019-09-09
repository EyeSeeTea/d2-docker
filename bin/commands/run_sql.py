import utils

DESCRIPTION = "Run SQL in running d2-docker container"
NAME = "run-sql"


def setup(parser):
    parser.add_argument(
        "sql_file",
        metavar="SQL_FILE",
        nargs="?",
        help="SQL file (if empty, open interactive psql terminal)",
    )


def run(args):
    image_name = utils.get_running_image_name()
    sql_file = args.sql_file
    if sql_file:
        utils.logger.info("Run SQL file {} for image {}".format(sql_file, image_name))

    status = utils.get_image_status(image_name)
    if status["state"] != "running":
        raise utils.D2DockerError("Container must be running to build image: {}".format(image_name))

    db_container = status["containers"]["db"]
    psql_cmd = ["psql", "-U", "dhis", "dhis2"]
    cmd = ["docker", "exec", ("-i" if sql_file else "-it"), db_container, *psql_cmd]
    result = utils.run(cmd, stdin=(open(sql_file) if sql_file else None), raise_on_error=False)

    if result.returncode != 0:
        utils.logger.error("Could not execute the SQL file, is the container running?")
        return 1
