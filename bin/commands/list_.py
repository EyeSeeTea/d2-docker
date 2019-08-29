import utils

DESCRIPTION = "List d2-docker data images"
NAME = "list"


def setup(parser):
    pass


def run(args):
    utils.logger.info("Listing docker images with pattern: {}".format(utils.DHIS2_DATA_IMAGE))
    running_containers = get_running_containers()
    images_info = get_images_info(running_containers)
    print("\n".join(sorted(images_info)))


def get_images_info(running_containers):
    """Get a list of images info: "{NAME} STOPPED" or "{NAME} RUNNING[port={N}]"."""
    cmd_image = ["docker", "image", "ls", "--format={{.Repository}} {{.Tag}}"]
    result_image = utils.run(cmd_image, capture_output=True)
    lines_parts = [line.split() for line in result_image.stdout.decode("utf-8").splitlines()]
    data_image_names = []

    for entry in lines_parts:
        if len(entry) != 2:
            continue
        repo, tag = entry
        image_name = repo + ":" + tag

        if utils.DHIS2_DATA_IMAGE in repo:
            port = running_containers.get(image_name, None)
            state = "RUNNING[port={}]".format(port) if port else "STOPPED"
            value = "{} {}".format(image_name, state)
            data_image_names.append(value)

    return data_image_names


def get_running_containers():
    """Return dictionary of {DATA_IMAGE_NAME: PORT} of active d2-docker instances."""
    cmd_ps = ["docker", "ps", '--format={{.Label "com.eyeseetea.image-name"}} {{.Ports}}']
    result_ps = utils.run(cmd_ps, capture_output=True)
    lines_parts_ps = [line.split(None, 1) for line in result_ps.stdout.decode("utf-8").splitlines()]

    running_containers = {}
    for entry in lines_parts_ps:
        if len(entry) != 2:
            continue
        image_name, ports = entry
        port = utils.get_port_from_docker_ports(ports)
        if port:
            running_containers[image_name] = port
    return running_containers
