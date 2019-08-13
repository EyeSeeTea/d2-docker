import argparse
import logging

import utils

DESCRIPTION = "Push dhis2-db docker image"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Docker dhis2-db image")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    logging.info("Push image: {}".format(image_name))
    utils.run(["docker", "push", image_name])
