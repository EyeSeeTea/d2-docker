import logging
import os

import utils
from . import commit

DESCRIPTION = "Copy databases from/to docker containers"


def setup(parser):
    parser.add_argument("source", metavar="SOURCE", type=str, help="Source (image or data folder)")
    parser.add_argument(
        "destinations",
        metavar="DESTINATION",
        type=str,
        nargs="+",
        help="Destinations (images or data folders)",
    )


def get_item_type(name):
    if os.path.exists(name) and os.path.isdir(name):
        return "folder"
    else:
        return "docker-image"


def run(args):
    source = args.source
    source_type = get_item_type(source)
    block_function = commit.running_container if source_type == "docker-image" else utils.noop

    with block_function(source) as status:
        for dest in args.destinations:
            dest_type = get_item_type(dest)
            logging.info("Copying: {}:{} -> {}:{}".format(source_type, source, dest_type, dest))

            if source_type == "docker-image" and dest_type == "docker-image":
                commit.copy_image(args.dhis2_db_docker_directory, source, dest)
            elif source_type == "docker-image" and dest_type == "folder":
                container_name = status["containers"]["db"]
                commit.export_data(source, container_name, dest)
            else:
                raise utils.D2DockerError("Not implemented")
