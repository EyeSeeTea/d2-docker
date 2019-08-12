import subprocess
import logging
import re

PROJECT_NAME_PREFIX = "d2-docker"


class D2DockerError(Exception):
    pass


def get_clean_image_name(image_name):
    """Return a string suitable to be used in a container name."""
    return re.sub(r"[^\w]", "_", image_name)


def run(command_parts, check=True, env=None, capture_output=False):
    """Run command and return the result object."""
    logging.debug("Env: {}".format(env))
    logging.debug("Run: {}".format(subprocess.list2cmdline(command_parts)))
    return subprocess.run(command_parts, check=check, env=env, capture_output=capture_output)


def get_running_image_name():
    """Return the name of the single running d2-docker image. Otherwise, raise an error."""
    result = run(
        ["docker", "ps", '--format={{.Names}} {{.Label "com.eyeseetea.image-name"}}'],
        capture_output=True,
    )
    output_lines = result.stdout.decode("utf-8").splitlines()
    matching_lines = [
        line.split()[1]
        for line in output_lines
        if len(line.split()) == 2 and line.split()[0].startswith(PROJECT_NAME_PREFIX)
    ]

    if len(matching_lines) == 0:
        raise D2DockerError("There are no d2-docker images running")
    elif len(matching_lines) == 1:
        return matching_lines[0]
    else:
        raise D2DockerError(
            "There are more than one d2-docker images running, you must give an image name"
        )


def get_available_port(image_name, first_port=8080):
    """Return available port for an image. If it's already running, raise an error."""
    project_name = get_project_name(image_name)
    result = run(["docker", "ps", "--format={{.Names}} {{.Ports}}"], capture_output=True)
    output_lines = result.stdout.decode("utf-8").splitlines()
    port_re = r"0\.0\.0\.0:(\d+)->"
    running_containers = [
        line for line in output_lines if line.startswith(project_name) and re.search(port_re, line)
    ]

    if running_containers:
        raise D2DockerError("Image already runnning: {}".format(running_containers[0]))
    else:
        string_ports = re.findall(port_re, " ".join(output_lines))
        sorted_ports = sorted([int(string_port) for string_port in string_ports])
        return sorted_ports[-1] + 1 if sorted_ports else first_port


def get_project_name(image_name):
    """
    Return the project name prefix from an image name.

    The final containers created will be: PROJECT_NAME_{SERVICE}_1.
    """
    clean_image_name = get_clean_image_name(image_name)
    return "{}-{}".format(PROJECT_NAME_PREFIX, clean_image_name)


def run_docker_compose(args, image_name=None, port=None):
    """Run a docker-compose command for an image (if empty, auto-detect it)."""
    final_image_name = image_name or get_running_image_name()
    project_name = get_project_name(final_image_name)
    env = {"DHIS2_DATA_IMAGE": final_image_name, "DHIS2_CORE_PORT": str(port or 8080)}
    run(["docker-compose", "-p", project_name] + args, env=env)
