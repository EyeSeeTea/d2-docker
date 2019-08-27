import logging
import os
import re

import utils

DESCRIPTION = "Start a container from an existing dhis2-db Docker image or from an exported file"
DHIS2_DB_IMAGE_RE = "/dhis2-db:"


def setup(parser):
    parser.add_argument(
        "image_or_file",
        metavar="IMAGE_OR_EXPORT_FILE",
        type=str,
        help="Docker image or images file",
    )
    parser.add_argument(
        "-d", "--detach", action="store_true", help="Run container on the background"
    )
    parser.add_argument("-p", "--pull", action="store_true", help="Force a pull from docker hub")


def run(args):
    image_or_file = args.image_or_file

    if os.path.exists(image_or_file) and os.path.isfile(image_or_file):
        image_name = import_from_file(image_or_file)
        start(args, image_name)
    else:
        start(args, image_or_file)


def import_from_file(images_path):
    result = utils.load_images_file(images_path)
    lines = result.stdout.decode("utf-8").splitlines()
    lines_splitted = [line.split() for line in lines]
    dhis2_db_images = [
        parts[-1] for parts in lines_splitted if parts and re.search(DHIS2_DB_IMAGE_RE, parts[-1])
    ]
    if dhis2_db_images:
        return dhis2_db_images[0]
    else:
        msg = "Cannot find dhis2-db image (pattern={})".format(DHIS2_DB_IMAGE_RE)
        raise utils.D2DockerError(msg)


def start(args, image_name):
    logging.info("Start image: {}".format(image_name))
    result = utils.get_image_status(image_name)
    if result["state"] == "running":
        msg = "Container already runnning for image {}".format(result["containers"]["db"])
        raise utils.D2DockerError(msg)
    port = utils.get_free_port()

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
