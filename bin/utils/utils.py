import subprocess
import logging
import re
import socket

PROJECT_NAME_PREFIX = "d2-docker"


class D2DockerError(Exception):
    pass


def run(command_parts, check=True, env=None, capture_output=False, **kwargs):
    """Run command and return the result subprocess object."""
    cmd = subprocess.list2cmdline(command_parts)
    logging.debug("Run: {}".format(cmd))

    if env:
        logging.debug("Env: {}".format(env))
    try:
        return subprocess.run(
            command_parts, check=check, env=env, capture_output=capture_output, **kwargs
        )
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
        raise D2DockerError("There are no d2-docker images running, specify image name")
    elif len(image_names) == 1:
        logging.info("Running image: {}".format(image_names[0]))
        return image_names[0]
    else:
        raise D2DockerError(
            "{} d2-docker images running, specify an image name".format(len(images_names))
        )


def get_free_port(start=8080, end=65535):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            port_is_open = sock.connect_ex(("localhost", port)) == 0
            if not port_is_open:
                return port
    raise D2DockerError("No free open available")


def get_image_status(image_name, first_port=8080):
    """Return a Result(status=True, value=value) available port for an image.
    If it's already running, return Result(status=False, error=error)."""
    final_image_name = image_name or get_running_image_name()
    project_name = get_project_name(final_image_name)
    result = run(["docker", "ps", "--format={{.Names}} {{.Ports}}"], capture_output=True)
    output_lines = result.stdout.decode("utf-8").splitlines()
    port_re = r"0\.0\.0\.0:(\d+)->"

    containers = {}
    port = None

    for line in output_lines:
        parts = line.split(None, 1)
        container_name, ports = parts
        if container_name.startswith(project_name + "_"):
            service = container_name[len(project_name) + 1 :].split("_", 1)[0]
            containers[service] = container_name
            if service == "gateway":
                port = re.match(port_re, ports).group(1)

    if containers and port:
        return {"status": "running", "containers": containers, "port": int(port)}
    else:
        return {"status": "stopped"}


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

    return run(["docker-compose", "-p", project_name] + args, env=env, **kwargs)
