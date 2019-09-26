from d2_docker import utils

DESCRIPTION = "Stop docker containers"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Docker image")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    utils.logger.info("Stop container for image: {}".format(image_name))
    utils.run_docker_compose(["stop"], image_name)
