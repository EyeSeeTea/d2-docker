from d2_docker import utils

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


def run(args):
    source = args.source
    docker_dir = utils.get_docker_directory("data", args)
    copy(source, args.destinations, docker_dir)


def copy(source, destinations, docker_dir):
    logger = utils.logger
    source_type = utils.get_item_type(source)
    logger.debug("Source {} has type: {}".format(source, source_type))

    for dest in destinations:
        dest_type = utils.get_item_type(dest)
        logger.debug("Destination {} has type: {}".format(dest, dest_type))
        logger.info("Copying: {}:{} -> {}:{}".format(source_type, source, dest_type, dest))

        if source_type == "docker-image" and dest_type == "docker-image":
            utils.copy_image(docker_dir, source, dest)
        elif source_type == "docker-image" and dest_type == "folder":
            utils.export_data_from_image(source, dest)
        elif source_type == "folder" and dest_type == "docker-image":
            utils.build_image_from_directory(docker_dir, source, dest)
        elif source_type == "folder" and dest_type == "folder":
            utils.copytree(source, dest)
        else:
            raise utils.D2DockerError("Not implemented")

        logger.info("Done")
