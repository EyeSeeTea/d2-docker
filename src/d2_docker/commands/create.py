import os
import shutil

from d2_docker import utils

DESCRIPTION = "Create d2-docker images"


def setup(parser):
    subparser = parser.add_subparsers(help="Image type", dest="type")

    core_parser = subparser.add_parser("core", help="Create core image")
    core_parser.add_argument("core_image", metavar="IMAGE", help="Image core name")
    core_parser.add_argument("-v", "--version", help="DHIS2 version (https://releases.dhis2.org/)")
    core_parser.add_argument("--war", help="WAR file")
    core_parser.add_argument("--dhis2-home", metavar="FILE", nargs="+", help="DHIS2_HOME file")

    data_parser = subparser.add_parser("data", help="Create data image")
    data_parser.add_argument("data_image", metavar="IMAGE", help="Image core name")
    data_parser.add_argument("--sql", help="Supported sql / sql.gz / dump formats")
    data_parser.add_argument("--apps-dir", help="Directory containing Dhis2 apps")
    data_parser.add_argument("--documents-dir", help="Directory containing Dhis2 documents")
    data_parser.add_argument("--datavalues-dir", help="Directory containing Dhis2 datavalues(file resources)")


def run(args):
    if args.type == "core":
        create_core(args)
    elif args.type == "data":
        create_data(args)
    else:
        raise utils.D2DockerError("Unknown subcommand for create: {}".format(args.type))


def create_core(args):
    docker_dir = utils.get_docker_directory("core", args)
    utils.create_core(
        docker_dir=docker_dir,
        image=args.core_image,
        version=args.version,
        war=args.war,
        dhis2_home_paths=args.dhis2_home,
    )


def create_data(args):
    image = args.data_image
    docker_dir = utils.get_docker_directory("data", args)
    utils.logger.info("Create data image: {}".format(image))

    with utils.temporal_build_directory(docker_dir) as build_dir:
        db_path = os.path.join(build_dir, "db/")
        utils.mkdir_p(db_path)
        if args.apps_dir:
            dest_apps_dir = os.path.join(build_dir, "apps")
            utils.logger.debug("Copy apps: {} -> {}".format(args.apps_dir, dest_apps_dir))
            utils.copytree(args.apps_dir, dest_apps_dir)
        if args.documents_dir:
            dest_documents_dir = os.path.join(build_dir, "document")
            utils.logger.debug(
                "Copy documents: {} -> {}".format(args.documents_dir, dest_documents_dir)
            )
            utils.copytree(args.documents_dir, dest_documents_dir)
        if args.datavalues_dir:
            dest_datavalues_dir = os.path.join(build_dir, "dataValue")
            utils.logger.debug(
                "Copy datavalues: {} -> {}".format(args.datavalues_dir, dest_datavalues_dir)
            )
            utils.copytree(args.datavalues_dir, dest_datavalues_dir)
        if args.sql:
            utils.logger.debug("Copy DB file:  {} -> {}".format(args.sql, db_path))
            shutil.copy(args.sql, db_path)

        utils.run(["docker", "build", build_dir, "--tag", image])
