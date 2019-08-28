import utils

DESCRIPTION = "Run SQL for a  d2-docker image and commit the result"
NAME = "run-sql"


def setup(parser):
    parser.add_argument("-i", "--image", metavar="IMAGE", type=str, help="Docker dhis2-db image")
    parser.add_argument("sql_file", metavar="SQL_FILE", type=str, help="SQL file")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    sql_file = args.sql_file
    utils.logger.info("Run SQL file {} for image {}".format(sql_file, image_name))
    cmd = ["exec", "-T", "db", "psql", "-U", "dhis", "dhis2"]
    result = utils.run_docker_compose(cmd, image_name, stdin=open(sql_file), raise_on_error=False)
    if result.returncode != 0:
        utils.logger.error("Could not execute the SQL file, is the container running?")
        return 1
