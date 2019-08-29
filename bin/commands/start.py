import os
import re

import utils

DESCRIPTION = "Start a container from an existing dhis2-data Docker image or from an exported file"


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
    dhis2_data_image_re = "/{}:".format(utils.DHIS2_DATA_IMAGE)
    result = utils.load_images_file(images_path)
    lines = result.stdout.decode("utf-8").splitlines()
    lines_splitted = [line.split() for line in lines]
    dhis2_data_images = [
        parts[-1] for parts in lines_splitted if parts and re.search(dhis2_data_image_re, parts[-1])
    ]
    if dhis2_data_images:
        return dhis2_data_images[0]
    else:
        msg = "Cannot find dhis2-data image (pattern={})".format(dhis2_data_image_re)
        raise utils.D2DockerError(msg)


def start(args, image_name):
    utils.logger.info("Start image: {}".format(image_name))
    result = utils.get_image_status(image_name)
    if result["state"] == "running":
        msg = "Container already runnning for image {}".format(result["containers"]["db"])
        raise utils.D2DockerError(msg)
    port = utils.get_free_port()

    if args.pull:
        utils.run_docker_compose(["pull"], image_name)

    utils.run_docker_compose(["down", "--volumes"], image_name)

    up_args = ["--force-recreate", *(["--detach"] if args.detach else [])]
    try:
        utils.run_docker_compose(["up", *up_args], image_name, port=port)
    except KeyboardInterrupt:
        utils.logger.info("Control+C pressed, stopping containers")
        utils.run_docker_compose(["stop"], image_name)

    if args.detach:
        utils.logger.info("Detaching... run d2-docker logs to see logs")
