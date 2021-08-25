from d2_docker import utils

DESCRIPTION = "List d2-docker data images"
NAME = "list"


def setup(_parser):
    pass


def run(_args):
    utils.logger.debug("Listing docker images with pattern: {}".format(utils.DHIS2_DATA_IMAGE))
    running_containers = get_running_containers()
    images_info = get_images_info(running_containers)
    sorted_values = sorted(images_info, key=lambda val: val["port"] or 1e9)
    print("\n".join(val["text"] for val in sorted_values))


def get_images_info(running_containers):
    cmd_image = ["docker", "image", "ls", "--format={{.Repository}} {{.Tag}}"]
    result_image = utils.run(cmd_image, capture_output=True)
    lines_parts = [line.split() for line in result_image.stdout.decode("utf-8").splitlines()]
    data_image_names = []
    void_tag = "<none>"

    for entry in lines_parts:
        if len(entry) != 2:
            continue
        repo, tag = entry
        if void_tag in repo or void_tag in tag:
            continue
        image_name = repo + ":" + tag

        if utils.DHIS2_DATA_IMAGE in repo:
            info = running_containers.get(image_name, None) or {}
            port = info.get("port", None)

            if port:
                deploy_path = info.get("deploy_path", None)
                extra_info = ",".join(
                    filter(
                        bool,
                        [
                            "port={}".format(port),
                            "deploy_path={}".format(deploy_path) if deploy_path else None,
                        ],
                    )
                )
                state = "RUNNING[{}]".format(extra_info)
            else:
                state = "STOPPED"
            value = {
                "port": port,
                "text": "{} {}".format(image_name, state),
            }
            data_image_names.append(value)

    return data_image_names


def get_running_containers():
    """Return dictionary of {DATA_IMAGE_NAME: PORT} of active d2-docker instances."""
    fmt = '{{.Label "com.eyeseetea.image-name"}} {{.Ports}} {{.Label "com.eyeseetea.deploy-path"}}'
    lines = utils.run_docker_ps(["--format=" + fmt])
    lines_parts_ps = [line.split(None, 2) for line in lines]

    running_containers = {}
    for entry in lines_parts_ps:
        if len(entry) == 2:
            image_name, ports = entry
            deploy_path = ""
        elif len(entry) == 3:
            image_name, ports, deploy_path = entry
        else:
            continue
        port = utils.get_port_from_docker_ports(ports)
        if port:
            running_containers[image_name] = dict(port=port, deploy_path=deploy_path)
    return running_containers
