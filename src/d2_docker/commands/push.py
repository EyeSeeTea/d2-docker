from d2_docker import utils

DESCRIPTION = "Push dhis2-data docker image"


def setup(parser):
    parser.add_argument(
        "--with-core", action="store_true", help="Push also dhis2-core companion image"
    )
    parser.add_argument(
        "image", metavar="IMAGE", type=str, nargs="?", help="Docker dhis2-data image"
    )


def run(args):
    data_image_name = args.image or utils.get_running_image_name()
    utils.logger.info("Push data image: {}".format(data_image_name))
    utils.push_image(data_image_name)

    if args.with_core:
        core_image_name = utils.get_core_image_name(data_image_name)
        utils.logger.info("Push core image: {}".format(core_image_name))
        utils.push_image(core_image_name)
