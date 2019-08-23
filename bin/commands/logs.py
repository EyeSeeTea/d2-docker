import logging

import utils

DESCRIPTION = "Show docker logs"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Hub docker image")
    parser.add_argument("-d", "--detach", action="store_true", help="Run container on background")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    logging.info("Show logs: {}".format(image_name))
    utils.run_docker_compose(["logs", "-f"], image_name)
