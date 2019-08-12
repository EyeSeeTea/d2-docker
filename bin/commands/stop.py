import argparse
import logging

from . import utils

DESCRIPTION = "Stop docker containers"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Docker image")


def run(args):
    logging.info("Stop container for image: {}".format(args.image))
    utils.run_docker_compose(["stop"], args.image)
