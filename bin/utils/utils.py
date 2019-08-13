import subprocess
import logging
import re

PROJECT_NAME_PREFIX = "d2-docker"


class D2DockerError(Exception):
    pass


def run(command_parts, check=True, env=None, **kwargs):
    """Run command and return the result subprocess object."""
    cmd = subprocess.list2cmdline(command_parts)
    logging.debug("Run: {}".format(cmd))
    if env:
        logging.debug("Env: {}".format(env))
    try:
        return subprocess.run(command_parts, check=check, env=env, **kwargs)
    except subprocess.CalledProcessError as exc:
        raise D2DockerError("Command failed with code {}: {}".format(exc.returncode, cmd))


def get_running_image_name():
    """Return the name of the single running d2-docker image. Otherwise, raise an error."""
    result = run(
        ["docker", "ps", '--format={{.Names}} {{.Label "com.eyeseetea.image-name"}}'],
        capture_output=True,
    )
    output_lines = result.stdout.decode("utf-8").splitlines()
    image_names = [
        line_parts[1]
        for line_parts in [line.split() for line in output_lines]
        if len(line_parts) == 2 and line_parts[0].startswith(PROJECT_NAME_PREFIX)
    ]

    if len(image_names) == 0:
        raise D2DockerError("There are no d2-docker images running")
    elif len(image_names) == 1:
        logging.info("Running image: {}".format(image_names[0]))
        return image_names[0]
    else:
        raise D2DockerError(
            "{} d2-docker images running, specify an image name".format(len(images_names))
        )


def get_available_port(image_name, first_port=8080):
    """Return a Result(status=True, value=value) available port for an image.
    If it's already running, return Result(status=False, error=error)."""
    final_image_name = image_name or get_running_image_name()
    project_name = get_project_name(final_image_name)
    result = run(["docker", "ps", "--format={{.Names}} {{.Ports}}"], capture_output=True)
    output_lines = result.stdout.decode("utf-8").splitlines()
    port_re = r"0\.0\.0\.0:(\d+)->"
    running_containers = [
        line for line in output_lines if line.startswith(project_name) and re.search(port_re, line)
    ]

    if running_containers:
        return {"status": "running", "image": running_containers[0]}
    else:
        string_ports = re.findall(port_re, " ".join(output_lines))
        sorted_ports = sorted([int(string_port) for string_port in string_ports])
        port = (sorted_ports[-1] + 1) if sorted_ports else first_port
        return {"status": "port_available", "port": port}


def get_project_name(image_name):
    """
    Return the project name prefix from an image name.

    The final containers created will be: PROJECT_NAME_{SERVICE}_1.
    """
    clean_image_name = re.sub(r"[^\w]", "_", image_name)
    return "{}-{}".format(PROJECT_NAME_PREFIX, clean_image_name)


def run_docker_compose(args, image_name=None, port=None, **kwargs):
    """Run a docker-compose command for an image (if empty, auto-detect it)."""
    final_image_name = image_name or get_running_image_name()
    project_name = get_project_name(final_image_name)
    env_pairs = [
        ("DHIS2_DATA_IMAGE", final_image_name),
        ("DHIS2_CORE_PORT", str(port)) if port else None,
    ]
    env = dict((k, v) for (k, v) in [pair for pair in env_pairs if pair] if v)

    run(["docker-compose", "-p", project_name] + args, env=env, **kwargs)
