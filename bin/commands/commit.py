import utils

DESCRIPTION = "Commit docker images"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Docker image")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    docker_dir = utils.get_docker_directory(args.dhis2_db_docker_directory)
    utils.logger.info("Commit image: {}".format(image_name))

    with utils.running_container(image_name):
        utils.build_image_from_source(docker_dir, image_name, image_name)
