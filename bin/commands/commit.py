import utils

DESCRIPTION = "Commit docker images"


def setup(parser):
    parser.add_argument(
        "dest_image",
        metavar="DESTINATION_IMAGE",
        nargs="?",
        help="Destination Docker image (same if empty)",
    )


def run(args):
    image_name = utils.get_running_image_name()
    docker_dir = utils.get_docker_directory(args.dhis2_data_docker_directory)
    utils.logger.info("Commit image: {}".format(image_name))
    utils.build_image_from_source(docker_dir, image_name, args.dest_image or image_name)
