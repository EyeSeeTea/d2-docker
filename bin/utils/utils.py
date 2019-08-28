import subprocess
import logging
import re
import os
import socket
import tempfile
from contextlib import contextmanager
from distutils import dir_util

PROJECT_NAME_PREFIX = "d2-docker"


def get_logger():
    logger = logging.getLogger("root")
    formatter = logging.Formatter("[d2-docker:%(levelname)s] %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = get_logger()


class D2DockerError(Exception):
    pass


def mkdir_p(path):
    """Create directory. Do nothing if it exists."""
    os.makedirs(path, exist_ok=True)


def copytree(source, dest):
    """Copy full tree path from source to dest, create dest if it does not exists."""
    dir_util.copy_tree(source, dest)


def run(command_parts, raise_on_error=True, env=None, capture_output=False, **kwargs):
    """Run command and return the result subprocess object."""
    cmd = subprocess.list2cmdline(command_parts)

    if env:
        env_vars = ("{}={}".format(k, v) for (k, v) in env.items())
        logger.debug("Environment: {}".format(" ".join(env_vars)))

    try:
        logger.debug("Run: {}".format(cmd))
        return subprocess.run(
            command_parts, check=raise_on_error, env=env, capture_output=capture_output, **kwargs
        )
    except subprocess.CalledProcessError as exc:
        raise D2DockerError("Command failed with code {}: {}".format(exc.returncode, cmd))


def get_free_port(start=8080, end=65535):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            port_is_open = sock.connect_ex(("localhost", port)) == 0
            if not port_is_open:
                return port
    raise D2DockerError("No free open available")


@contextmanager
def noop(image_name):
    """Do nothing with-statament context."""
    yield {}


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
        logger.info("Running image: {}".format(image_names[0]))
        return image_names[0]
    else:
        raise D2DockerError(
            "{} d2-docker images running, specify an image name".format(len(image_names))
        )


def get_image_status(image_name, first_port=8080):
    """
    If the container for the image is not running, return:

        {
            "state": "stopped"
        }

    If it's running, return:

        {
            "state": "running",
            "containers": {
                "core": CONTAINER_CORE,
                "gateway": CONTAINER_GATEWAY,
                "db": CONTAINER_DB,
            },
            "port": PORT,
        }
    Return a Result(status=True, value=value) available port for an image.
    If it's already running, return Result(status=False, error=error).
    """
    final_image_name = image_name or get_running_image_name()
    project_name = get_project_name(final_image_name)
    result = run(["docker", "ps", "--format={{.Names}} {{.Ports}}"], capture_output=True)
    output_lines = result.stdout.decode("utf-8").splitlines()

    containers = {}
    port = None

    for line in output_lines:
        parts = line.split(None, 1)
        container_name, ports = parts
        if container_name.startswith(project_name + "_"):
            service = container_name[len(project_name) + 1 :].split("_", 1)[0]
            containers[service] = container_name
            if service == "gateway":
                port = get_port_from_docker_ports(ports)

    if containers and port:
        return {"state": "running", "containers": containers, "port": port}
    else:
        return {"state": "stopped"}


def get_port_from_docker_ports(info):
    port_re = r"0\.0\.0\.0:(\d+)->"
    match = re.match(port_re, info)
    port = int(match.group(1)) if match else None
    return port


def get_project_name(image_name):
    """
    Return the project name prefix from an image name.

    Example: eyeseetea/dhis2-db:2.30-ento -> eyeseetea-2-30-ento

    The final containers created have names: PROJECT_NAME_{SERVICE}_1.
    """
    clean_image_name1 = image_name.replace("/dhis2-db", "")
    clean_image_name2 = re.sub(r"[^\w]", "_", clean_image_name1)
    return "{}-{}".format(PROJECT_NAME_PREFIX, clean_image_name2)


def run_docker_compose(args, image_name=None, port=None, **kwargs):
    """Run a docker-compose command for an image (if empty, auto-detect it)."""
    final_image_name = image_name or get_running_image_name()
    project_name = get_project_name(final_image_name)
    env_pairs = [
        ("DHIS2_DATA_IMAGE", final_image_name),
        ("DHIS2_CORE_PORT", str(port)) if port else None,
    ]
    env = dict((k, v) for (k, v) in [pair for pair in env_pairs if pair] if v)

    return run(["docker-compose", "-p", project_name, *args], env=env, **kwargs)


def get_item_type(name):
    """
    Return "docker-image" if name matches the pattern 'ORG/dhis2-db:TAG',
    otherwise assume it's a folder.
    """
    namespace_split = name.split("/")
    if len(namespace_split) != 2:
        return "folder"
    else:
        name_tag_split = namespace_split[1].split(":")
        if len(name_tag_split) == 2 and name_tag_split[0] == "dhis2-db":
            return "docker-image"
        else:
            return "folder"


def get_docker_directory(dhis2_db_docker_directory=None):
    """Return docker directory for dhis2-db."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_dir = os.path.join(script_dir, "../..", "images/dhis2-db")
    docker_dir = dhis2_db_docker_directory or os.path.realpath(default_dir)

    if not os.path.isdir(docker_dir):
        raise D2DockerError("Docker directory not found: {}".format(docker_dir))
    else:
        logger.debug("Docker directory: {}".format(docker_dir))
        return docker_dir


@contextmanager
def running_container(image_name):
    """
    Return a context manager to use with a with statament, making sure a container for image
    is running and the container ends in the same state it has before.
    """
    status1 = get_image_status(image_name)
    logger.debug("Status for {}: {}".format(image_name, status1))
    container_is_running_on_start = status1["state"] == "running"

    if not container_is_running_on_start:
        logger.info("Container not running for image, start it: {}".format(image_name))
        run_docker_compose(["up", "--detach"], image_name, port=get_free_port())

    try:
        status2 = get_image_status(image_name)
        logger.debug("Status for {}: {}".format(image_name, status2))
        yield status2
    finally:
        if container_is_running_on_start:
            logger.info("Container was running on start, keep it running: {}".format(image_name))
        else:
            logger.info("Container was not running on start, stop it: {}".format(image_name))
            run_docker_compose(["stop"], image_name)


def build_image_from_source(docker_dir, source_image_name, dest_image_name):
    """Build a docker image using another one as template."""
    status = get_image_status(source_image_name)
    if status["state"] != "running":
        raise D2DockerError("Container must be running to build image")
    db_container_name = status["containers"]["db"]

    with tempfile.TemporaryDirectory() as temp_dir_root:
        logger.info("Create temporal directory: {}".format(temp_dir_root))
        temp_dir = os.path.join(temp_dir_root, "contents")

        logger.info("Copy base docker files: {}".format(docker_dir))
        copytree(docker_dir, temp_dir)
        export_data(source_image_name, db_container_name, temp_dir)
        run(["docker", "build", temp_dir, "--tag", dest_image_name])


def build_image_from_directory(docker_dir, data_dir, dest_image_name):
    """Build docker image from data (db + apps) directory."""
    with tempfile.TemporaryDirectory() as temp_dir_root:
        logger.info("Create temporal directory: {}".format(temp_dir_root))
        temp_dir = os.path.join(temp_dir_root, "contents")

        logger.info("Copy base docker files: {}".format(docker_dir))
        copytree(docker_dir, temp_dir)

        logger.info("Copy data: {} -> {}".format(data_dir, temp_dir))
        copytree(data_dir, temp_dir)
        run(["docker", "build", temp_dir, "--tag", dest_image_name])


def export_data(image_name, db_container_name, destination):
    """Export data (db + apps) from a running Docker container to a destination directory."""
    logger.info("Copy Dhis2 apps")
    source = "{}:/data/apps/".format(db_container_name)
    mkdir_p(destination)
    run(["docker", "cp", source, destination])

    db_path = os.path.join(destination, "db.sql.gz")
    export_database(image_name, db_path)


def export_database(image_name, db_path):
    """Export Dhis2 database into a gzipped file."""
    logger.info("Dump DB: {}".format(db_path))

    with open(db_path, "wb") as db_file:
        pg_dump = "pg_dump -U dhis dhis2 | gzip"
        # -T: Disable pseudo-tty allocation. Otherwise the compressed output pipe is corrupted.
        cmd = ["exec", "-T", "db", "bash", "-c", pg_dump]
        run_docker_compose(cmd, image_name, stdout=db_file)


def load_images_file(input_file):
    """Load docker images from local file."""
    return run(["docker", "load", "-i", input_file], capture_output=True)


def push_image(image_name):
    """Push Docker image to the repository."""
    return run(["docker", "push", image_name])


def save_images(image_names, output_file_path):
    """Save list of Docker images into a local file."""
    run(["docker", "save", *image_names, "-o", output_file_path])
