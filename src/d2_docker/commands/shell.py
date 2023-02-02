from d2_docker import utils

DESCRIPTION = "Run shell terminal in core container"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", help="Docker image name")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    utils.logger.info("Open shell for image: {}".format(image_name))
    status = utils.get_image_status(image_name)

    if status["state"] != "running":
        utils.logger.error("Container must be running to start a shell")
        return 1
    else:
        core_container = status["containers"]["core"]
        cmd = ["docker", "exec", "--interactive", "--tty", core_container, "bash"]
        utils.run(cmd)
