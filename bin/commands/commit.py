import logging
import os
import shutil
import tempfile
from contextlib import contextmanager

import utils

DESCRIPTION = "Commit docker images"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Docker image")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    logging.info("Commit image: {}".format(image_name))
    with running_container(image_name):
        copy_image(args.dhis2_db_docker_directory, image_name, image_name)


def copy_image(dhis2_db_docker_directory, image_name, dest_image_name):
    docker_dir = get_docker_directory(dhis2_db_docker_directory)
    logging.info("Docker directory: {}".format(docker_dir))
    build_image_from_source(docker_dir, image_name, dest_image_name)


@contextmanager
def running_container(image_name):
    status1 = utils.get_image_status(image_name)
    logging.debug("Status for {}: {}".format(image_name, status1))

    if not status1["state"] == "running":
        logging.info("Start container")
        utils.run_docker_compose(["up", "--detach"], image_name, port=utils.get_free_port())

    try:
        status2 = utils.get_image_status(image_name)
        logging.debug("Status for {}: {}".format(image_name, status2))
        yield status2
    except Exception as exc:
        raise exc
    finally:
        status3 = utils.get_image_status(image_name)
        if status3["state"] == "running":
            logging.info("Stop container")
            utils.run_docker_compose(["stop"], image_name)


def get_docker_directory(dhis2_db_docker_directory):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_dir = os.path.join(script_dir, "../..", "images/dhis2-db")
    docker_dir = dhis2_db_docker_directory or os.path.realpath(default_dir)

    if not os.path.isdir(docker_dir):
        raise utils.D2DockerError("Docker directory not found: {}".format(docker_dir))
    else:
        return docker_dir


def build_image_from_source(docker_dir, source_image_name, dest_image_name):
    status = utils.get_image_status(source_image_name)
    if status["state"] != "running":
        raise utils.D2DockerError("Container must be running to build image")
    db_container_name = status["containers"]["db"]

    with tempfile.TemporaryDirectory() as temp_dir_root:
        logging.info("Create temporal directory: {}".format(temp_dir_root))
        temp_dir = os.path.join(temp_dir_root, "contents")

        logging.info("Copy base docker files: {}".format(docker_dir))
        shutil.copytree(docker_dir, temp_dir)
        export_data(source_image_name, db_container_name, temp_dir)
        utils.run(["docker", "build", temp_dir, "--tag", dest_image_name])


def export_data(image_name, db_container_name, destination):
    logging.info("Copy Dhis2 apps")
    source = "{}:/data/apps/".format(db_container_name)
    utils.run(["docker", "cp", source, destination])

    db_path = os.path.join(destination, "db.sql.gz")
    export_database(image_name, db_path)


def export_database(image_name, db_path):
    logging.info("Dump DB: {}".format(db_path))

    with open(db_path, "wb") as db_file:
        pg_dump = "pg_dump -U dhis dhis2 | gzip"
        # -T: Disable pseudo-tty allocation. Otherwise the compressed output pipe is corrupted.
        cmd = ["exec", "-T", "db", "bash", "-c", pg_dump]
        utils.run_docker_compose(cmd, image_name, stdout=db_file)
