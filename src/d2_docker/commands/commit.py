from d2_docker import utils

DESCRIPTION = "Commit d2-docker data image"


def setup(parser):
    parser.add_argument(
        "image",
        metavar="DESTINATION_IMAGE",
        nargs="?",
        help="Destination Docker image (same if empty)",
    )
    parser.add_argument(
        "--folders",
        nargs="+",
        choices=utils.default_folders,
        help="Folders to include in the image",
    )

def run(args):
    image_name = args.image or utils.get_running_image_name()
    docker_dir = utils.get_docker_directory("data", args)
    temp_dir = utils.get_temp_base_directory(args)
    utils.logger.info("Commit image: {}".format(image_name))
    utils.build_image_from_source(docker_dir, image_name, image_name, temp_dir, args.folders)
