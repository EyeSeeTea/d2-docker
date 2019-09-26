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


def run(args):
    image_name = args.image or utils.get_running_image_name()
    sql_file = args.sql_file

    status = utils.get_image_status(image_name)
    is_running = status["state"] == "running"
    running_containers = utils.noop(status) if is_running else utils.running_containers

    with running_containers(image_name, "db") as status:
        db_container = status["containers"]["db"]
        utils.logger.debug("DB container: {}".format(db_container))
        psql_cmd = ["psql", "-U", "dhis", "dhis2"]
        cmd = ["docker", "exec", ("-i" if sql_file else "-it"), db_container, *psql_cmd]
        if sql_file:
            utils.logger.info("Run SQL file {} for image {}".format(sql_file, image_name))
        result = utils.run(cmd, stdin=(open(sql_file) if sql_file else None), raise_on_error=False)

        if result.returncode != 0:
            utils.logger.error("Could not execute SQL")
            return 1
