import argparse
import logging

from . import utils

DESCRIPTION = "Show docker logs"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Hub docker image")
    parser.add_argument(
        "detach", action="store_true", help="Detach and run container on background"
    )


def run(args):
    logging.info("Show logs: {}".format(args.image))
    utils.run_docker_compose(["logs", "-f"], args.image)
