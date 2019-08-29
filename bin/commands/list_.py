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
    cmd_image = ["docker", "image", "ls", "--format={{.Repository}} {{.Tag}}"]
    result_image = utils.run(cmd_image, capture_output=True)
    lines_parts = [line.split() for line in result_image.stdout.decode("utf-8").splitlines()]
    data_image_names = []
    for repo, tag in lines_parts:
        image_name = (repo + ":" + tag) if repo != "<none>" and tag != "<none>" else None

        if image_name and utils.DHIS2_DATA_IMAGE in repo:
            project_name = utils.get_project_name(image_name)
            service_core = project_name + "_gateway_1"
            port = running_containers.get(service_core, None)
            state = "RUNNING[port={}]".format(port) if port else "STOPPED"
            value = "{} {}".format(image_name, state)
            data_image_names.append(value)

    return data_image_names


def get_running_containers():
    cmd_ps = ["docker", "ps", "--format={{.Names}} {{.Ports}}"]
    result_ps = utils.run(cmd_ps, capture_output=True)
    lines_parts_ps = [line.split() for line in result_ps.stdout.decode("utf-8").splitlines()]
    get_port = utils.get_port_from_docker_ports

    running_containers = {}
    for names, ports in lines_parts_ps:
        port = get_port(ports)
        if port:
            running_containers[names] = port
    return running_containers
