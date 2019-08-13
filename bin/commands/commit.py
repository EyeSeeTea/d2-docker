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


def copy_files(src_dir, dest_dir):
    src_files = os.listdir(src_dir)
    for file_name in src_files:
        full_file_name = os.path.join(src_dir, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, dest_dir)


def run(args):
    logging.info("Commit image: {}".format(args.image))
    script_dir = os.path.dirname(os.path.realpath(__file__))
    docker_dir = args.dhis2_db_docker_directory or os.path.realpath(
        os.path.join(script_dir, "../..", "images/dhis2-db")
    )

    if not os.path.isdir(docker_dir):
        raise utils.D2DockerError("Docker directory not found: {}".format(docker_dir))

    image_name = args.image or utils.get_running_image_name()
    result = utils.get_available_port(image_name)

    running_port = result["port"] if result["status"] == "port_available" else None

    if running_port:
        # Container not running, we need to start it
        utils.run_docker_compose(["up", "--detach"], image_name, port=running_port)

    with tempfile.TemporaryDirectory() as temp_dir:
        logging.debug("Create temporal directory: {}".format(temp_dir))

        logging.debug("Copy docker files: {}".format(docker_dir))
        copy_files(docker_dir, temp_dir)

        db_path = os.path.join(temp_dir, "db.sql.gz")
        logging.debug("Dump DB: {}".format(db_path))
        with open(db_path, "wb") as db_file:
            pg_dump = "pg_dump -U dhis dhis2 | gzip"
            # -T: Disable pseudo-tty allocation. Otherwise the compressed output pipe is corrupted.
            cmd = ["exec", "-T", "db", "bash", "-c", pg_dump]
            utils.run_docker_compose(cmd, args.image, stdout=db_file)

        utils.run(["docker", "build", temp_dir, "--tag", image_name])

    if running_port:
        # Container was not running, keep it stopped as it was
        utils.run_docker_compose(["stop"], image_name)
