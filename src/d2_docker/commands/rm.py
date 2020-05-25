from d2_docker import utils

DESCRIPTION = "Remove dhis2-data docker images/containers"


def setup(parser):
    parser.add_argument("images", metavar="IMAGE", nargs="+", help="Docker dhis2-data images")


def run(args):
    for image in args.images:
        remove_image(image)


def remove_image(image):
    utils.logger.info("Delete image/containers: {}".format(image))
    utils.run_docker_compose(["stop"], image)
    result = utils.run_docker_compose(["ps", "-q"], data_image=image, capture_output=True)
    container_ids = result.stdout.decode("utf-8").splitlines()
    utils.logger.debug("Container IDs: {}".format(container_ids))
    if container_ids:
        utils.run_docker(["container", "rm", *container_ids])
    utils.run_docker(["image", "rm", image])
    utils.logger.info("Removed: {}".format(image))
