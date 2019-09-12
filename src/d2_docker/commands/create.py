import contextlib
import os
import shutil
import tempfile
import urllib.request

from d2_docker import utils

DESCRIPTION = "Create d2-docker images"

RELEASES_BASEURL = "https://releases.dhis2.org"


def setup(parser):
    subparser = parser.add_subparsers(help="Image type", dest="type")

    core_parser = subparser.add_parser("core", help="Create core image")
    core_parser.add_argument("core_image", metavar="IMAGE", help="Image core name")
    core_parser.add_argument("-v", "--version", help="DHIS2 version (https://releases.dhis2.org/)")
    core_parser.add_argument("--war", help="WAR file")

    data_parser = subparser.add_parser("data", help="Create data image")
    data_parser.add_argument("data_image", metavar="IMAGE", help="Image core name")
    data_parser.add_argument("--sql", help="SQL .tar.gz file")
    data_parser.add_argument("--apps-dir", help="Directory containing Dhis2 apps")


def run(args):
    print(args)
    if args.type == "core":
        create_core(args)
    else:
        create_data(args)


@contextlib.contextmanager
def temporal_build_directory(args, image_type):
    docker_dir = utils.get_docker_directory(args, image_type)

    with tempfile.TemporaryDirectory() as build_dir:
        utils.logger.debug("Temporal directory: {}".format(build_dir))
        utils.copytree(docker_dir, build_dir)
        yield build_dir


def create_core(args):
    image = args.core_image
    utils.logger.info("Create core image: {}".format(image))

    with temporal_build_directory(args, "core") as build_dir:
        war_path = os.path.join(build_dir, "dhis.war")
        if args.version:
            war_url = "{}/{}/dhis.war".format(RELEASES_BASEURL, args.version)
            utils.logger.info("Download file: {}".format(war_url))
            urllib.request.urlretrieve(war_url, war_path)
        elif args.war:
            utils.logger.debug("Copy file: {} -> {}".format(args.war, war_path))
            shutil.copy(args.war, war_path)
        else:
            raise utils.D2DockerError("One option is required: --version | --war")

        utils.run(["docker", "build", build_dir, "--tag", image])


def create_data(args):
    image = args.data_image
    utils.logger.info("Create data image: {}".format(image))

    with temporal_build_directory(args, "data") as build_dir:
        if args.apps_dir:
            dest_apps_dir = os.path.join(build_dir, "apps")
            utils.logger.debug("Copy apps: {} -> {}".format(args.apps_dir, dest_apps_dir))
            utils.copytree(args.apps_dir, dest_apps_dir)
        if args.sql:
            sql_path = os.path.join(build_dir, "db.sql.gz")
            utils.logger.debug("Copy SQL file:  {} -> {}".format(args.sql, sql_path))
            shutil.copy(args.sql, sql_path)

        utils.run(["docker", "build", build_dir, "--tag", image])
