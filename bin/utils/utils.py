import subprocess
import logging
import re
import os
import socket
import tempfile
from distutils import dir_util

PROJECT_NAME_PREFIX = "d2docker"


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
    if capture_output:  # Option not available for python <= 3.6, emulate
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    if env:
        env_vars = ("{}={}".format(k, v) for (k, v) in env.items())
        logger.debug("Environment: {}".format(" ".join(env_vars)))

    try:
        logger.debug("Run: {}".format(cmd))
        return subprocess.run(command_parts, check=raise_on_error, env=env, **kwargs)
    except subprocess.CalledProcessError as exc:
        msg = "Command {} failed with code {}: {}"
        raise D2DockerError(msg.format(cmd, exc.returncode, exc.stderr))


def get_free_port(start=8080, end=65535):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            port_is_open = sock.connect_ex(("localhost", port)) == 0
            if not port_is_open:
                return port
    raise D2DockerError("No free open available")


def get_running_image_name():
    """Return the name of the single running d2-docker image. Otherwise, raise an error."""
    result = run(
        ["docker", "ps", '--format={{.Names}} {{.Label "com.eyeseetea.image-name"}}'],
        capture_output=True,
    )
    output_lines = result.stdout.decode("utf-8").splitlines()
    image_names = set(
        [
            line_parts[1]
            for line_parts in [line.split() for line in output_lines]
            if len(line_parts) == 2 and line_parts[0].startswith(PROJECT_NAME_PREFIX)
        ]
    )

    if len(image_names) == 0:
        raise D2DockerError("There are no d2-docker images running")
    elif len(image_names) == 1:
        image_name = list(image_names)[0]
        logger.info("Image is running: {}".format(image_name))
        return image_name
    else:
        names = "\n".join("  " + s for s in image_names)
        raise D2DockerError("Multiple d2-docker images running, specify one:\n{}".format(names))


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


DHIS2_DATA_IMAGE = "dhis2-data"


def get_project_name(image_name):
    """
    Return the project name prefix from an image name.

    Example: eyeseetea/dhis2-data:2.30-ento -> eyeseetea-2-30-ento

    The final containers created have names: PROJECT_NAME_{SERVICE}_1.
    """
    clean_image_name = image_name.replace("/" + DHIS2_DATA_IMAGE, "")
    name_with_prefix = "{}-{}".format(PROJECT_NAME_PREFIX, clean_image_name)
    return re.sub(r"[^\w]", "", name_with_prefix)


def get_core_image_name(data_image_name):
    """Return core image name from the data image.

    Example: eyeseetea/dhis2-data:2.30-sierra -> eyeseetea/dhis2-core:2.30
    """
    sp1 = data_image_name.split("/", 1)
    if len(sp1) != 2:
        raise D2DockerError("Invalid data image name: {}".format(data_image_name))
    namespace, name_with_tag = sp1
    sp2 = name_with_tag.split(":", 1)
    if len(sp2) != 2:
        raise D2DockerError("Invalid data image name: {}".format(data_image_name))
    name, tag = sp2
    sp3 = tag.split("-", 1)

    return "{}/dhis2-core:{}".format(namespace, sp3[0])


def run_docker_compose(
    args,
    data_image=None,
    core_image=None,
    port=None,
    load_from_data=True,
    post_sql_dir=None,
    scripts_dir=None,
    **kwargs,
):
    """
    Run a docker-compose command for a given image.

    If empty, check if there is one empty, and which port it's running listening to.

    The DHIS2_CORE_IMAGE is inferred from the data repo, if not specified.
    """
    final_image_name = data_image or get_running_image_name()
    project_name = get_project_name(final_image_name)
    core_image_name = core_image or get_core_image_name(data_image)

    check_directory_for_docker_volume(post_sql_dir)
    check_directory_for_docker_volume(scripts_dir)

    env_pairs = [
        ("DHIS2_DATA_IMAGE", final_image_name),
        ("DHIS2_CORE_PORT", str(port)) if port else None,
        ("DHIS2_CORE_IMAGE", core_image_name),
        ("LOAD_FROM_DATA", "yes" if load_from_data else "no"),
        # Set default values for directory, required by docker-compose volumes section
        ("POST_SQL_DIR", "./{}".format(post_sql_dir or ".post-sql")),
        ("SCRIPTS_DIR", "./{}".format(scripts_dir or ".scripts")),
    ]
    env = dict((k, v) for (k, v) in [pair for pair in env_pairs if pair] if v)

    return run(["docker-compose", "-p", project_name, *args], env=env, **kwargs)


def check_directory_for_docker_volume(directory):
    if directory and not os.path.isdir(directory) and os.path.isabs(directory):
        raise D2DockerError("Should be a relative directory: {}".format(directory))


def get_item_type(name):
    """
    Return "docker-image" if name matches the pattern 'ORG/{DHIS2_DATA_IMAGE}:TAG',
    otherwise assume it's a folder.
    """
    namespace_split = name.split("/")
    if len(namespace_split) != 2:
        return "folder"
    else:
        name_tag_split = namespace_split[1].split(":")
        if len(name_tag_split) == 2 and name_tag_split[0] == DHIS2_DATA_IMAGE:
            return "docker-image"
        else:
            return "folder"


def get_docker_directory(dhis2_data_docker_directory=None):
    """Return docker directory for dhis2-data."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_dir = os.path.join(script_dir, "../..", "images", DHIS2_DATA_IMAGE)
    docker_dir = dhis2_data_docker_directory or os.path.realpath(default_dir)

    if not os.path.isdir(docker_dir):
        raise D2DockerError("Docker directory not found: {}".format(docker_dir))
    else:
        logger.debug("Docker directory: {}".format(docker_dir))
        return docker_dir


def build_image_from_source(docker_dir, source_image, dest_image):
    """Build a docker image from source local directory."""
    status = get_image_status(source_image)
    if status["state"] != "running":
        raise D2DockerError("Container must be running to build image")

    with tempfile.TemporaryDirectory() as temp_dir_root:
        logger.info("Create temporal directory: {}".format(temp_dir_root))
        temp_dir = os.path.join(temp_dir_root, "contents")

        logger.info("Copy base docker files: {}".format(docker_dir))
        copytree(docker_dir, temp_dir)
        export_data_from_running_containers(source_image, status["containers"], temp_dir)
        run(["docker", "build", temp_dir, "--tag", dest_image])


def copy_image(docker_dir, source_image, dest_image):
    """Build a docker image using another one as template."""
    with tempfile.TemporaryDirectory() as temp_dir_root:
        logger.info("Create temporal directory: {}".format(temp_dir_root))
        temp_dir = os.path.join(temp_dir_root, "contents")

        logger.info("Copy base docker files: {}".format(docker_dir))
        copytree(docker_dir, temp_dir)
        export_data_from_image(source_image, temp_dir)
        run(["docker", "build", temp_dir, "--tag", dest_image])


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


def export_data_from_image(source_image, dest_path):
    result = run(["docker", "create", source_image], capture_output=True)
    container_id = result.stdout.decode("utf8").splitlines()[0]
    mkdir_p(dest_path)
    try:
        db_dest_path = os.path.join(dest_path, "db.sql.gz")
        run(["docker", "cp", container_id + ":" + "/data/db/00-base.db.sql.gz", db_dest_path])
        run(["docker", "cp", container_id + ":" + "/data/apps", dest_path])
    finally:
        run(["docker", "rm", "-v", container_id])


def export_data_from_running_containers(image_name, containers, destination):
    """Export data (db + apps) from a running Docker container to a destination directory."""
    logger.info("Copy Dhis2 apps")
    apps_source = "{}:/DHIS2_home/files/apps/".format(containers["core"])
    mkdir_p(destination)
    run(["docker", "cp", apps_source, destination])

    db_path = os.path.join(destination, "db.sql.gz")
    export_database(image_name, db_path)


def export_database(image_name, db_path):
    """Export Dhis2 database into a gzipped file."""
    logger.info("Dump DB: {}".format(db_path))
    mkdir_p(os.path.dirname(db_path))

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


def add_image_arg(parser):
    parser.add_argument("-i", "--image", metavar="IMAGE", type=str, help="Docker dhis2-data image")


def add_core_image_arg(parser):
    parser.add_argument(
        "-c", "--core-image", type=str, metavar="DOCKER_CORE_IMAGE", help="Docker dhis2-core image"
    )
