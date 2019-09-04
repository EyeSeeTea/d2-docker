import utils

DESCRIPTION = "Show docker logs"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", nargs="?", help="Hub docker image")
    parser.add_argument("-f", "--follow", action="store_true", help="Follow log output")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    utils.logger.info("Show logs: {}".format(image_name))
    args = ["logs", "-f" if args.follow else None]
    utils.run_docker_compose(filter(bool, args), image_name)
