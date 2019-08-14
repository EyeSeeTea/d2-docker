import argparse
import logging
import os
import shutil
import tempfile

import utils

DESCRIPTION = "Commit docker images"


def setup(parser):
    parser.add_argument("image", metavar="IMAGE", type=str, nargs="?", help="Docker image")
    parser.add_argument(
        "--dhis2-db-docker-directory",
        metavar="DIRECTORY",
        type=str,
        help="Directory container dhis2-db docker source",
    )


def run(args):
    image_name = args.image or utils.get_running_image_name()
    logging.info("Commit image: {}".format(image_name))

    docker_dir = get_docker_directory(args.dhis2_db_docker_directory)
    logging.info("Docker directory: {}".format(docker_dir))
    result = utils.get_image_status(image_name)
    is_running = result["status"] == "running"

    if not is_running:
        logging.info("Start container")
        utils.run_docker_compose(["up", "--detach"], image_name, port=utils.get_free_port())

    build_image(image_name, docker_dir)

    if not is_running:
        logging.info("Stop container")
        utils.run_docker_compose(["stop"], image_name)


def copy_files(src_dir, dest_dir):
    src_files = os.listdir(src_dir)
    for file_name in src_files:
        full_file_name = os.path.join(src_dir, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, dest_dir)


def get_docker_directory(dhis2_db_docker_directory):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_dir = os.path.join(script_dir, "../..", "images/dhis2-db")
    docker_dir = dhis2_db_docker_directory or os.path.realpath(default_dir)

    if not os.path.isdir(docker_dir):
        raise utils.D2DockerError("Docker directory not found: {}".format(docker_dir))
    else:
        return docker_dir


def build_image(image_name, docker_dir):
    result = utils.get_image_status(image_name)
    print(result)
    aa

    with tempfile.TemporaryDirectory() as temp_dir:
        logging.info("Create temporal directory: {}".format(temp_dir))

        logging.info("Copy docker files: {}".format(docker_dir))
        copy_files(docker_dir, temp_dir)

        db_path = os.path.join(temp_dir, "db.sql.gz")
        export_database(image_name, db_path)

        utils.run(["docker", "build", temp_dir, "--tag", image_name])


def export_database(image_name, db_path):
    logging.info("Dump DB: {}".format(db_path))

    with open(db_path, "wb") as db_file:
        pg_dump = "pg_dump -U dhis dhis2 | gzip"
        # -T: Disable pseudo-tty allocation. Otherwise the compressed output pipe is corrupted.
        cmd = ["exec", "-T", "db", "bash", "-c", pg_dump]
        utils.run_docker_compose(cmd, image_name, stdout=db_file)
