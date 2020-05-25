from d2_docker import utils

DESCRIPTION = "Pull dhis2-data docker image"


def setup(parser):
    parser.add_argument(
        "image", metavar="IMAGE", type=str, nargs="?", help="Docker dhis2-data image"
    )


def run(args):
    image_name = args.image or utils.get_running_image_name()
    utils.logger.info("Pull image: {}".format(image_name))
    utils.pull_image(image_name)
