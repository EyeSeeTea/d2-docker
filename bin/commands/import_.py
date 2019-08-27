import logging

import utils

NAME = "import"
DESCRIPTION = "Import d2-docker images from file"


def setup(parser):
    parser.add_argument("input_file", metavar="PATH", type=str, help="Input tar/tgz file")


def run(args):
    input_file = args.input_file
    logging.info("Load images from file: {}".format(input_file))
    utils.load_images_file(input_file)
