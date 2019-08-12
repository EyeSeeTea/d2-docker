import argparse
import logging

from . import utils

DESCRIPTION = "Start a container"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, help="Hub docker image")
    parser.add_argument(
        "-d", "--detach", action="store_true", help="Run container on the background"
    )
    parser.add_argument("-p", "--pull", action="store_true", help="Force a pull from docker hub")


def run(args):
    image_name = args.image
    logging.info("Start image: {}".format(image_name))
    port = utils.get_available_port(image_name)

    if args.pull:
        utils.run_docker_compose(["pull"], image_name)

    utils.run_docker_compose(["down", "--volumes"], image_name)

    up_args = ["--force-recreate"] + (["--detach"] if args.detach else [])
    try:
        utils.run_docker_compose(["up"] + up_args, image_name, port=port)
    except KeyboardInterrupt:
        logging.info("Control+C pressed, stopping containers")
        utils.run_docker_compose(["stop"], image_name)

    if args.detach:
        logging.info("Detaching... run d2-docker logs to see logs")
