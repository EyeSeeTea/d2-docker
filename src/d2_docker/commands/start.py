import os
import re

from d2_docker import utils

DESCRIPTION = "Start a container from an existing dhis2-data Docker image or from an exported file"


def setup(parser):
    server_xml_path = utils.get_config_file("server.xml")
    server_xml_help = "Use a custom Tomcat server.xml file. Template: {0}".format(server_xml_path)
    dhis_conf_path = utils.get_config_file("DHIS2_home/dhis.conf")
    dhis_conf_help = "Use a custom dhis.conf file. Template: {0}".format(dhis_conf_path)

    parser.add_argument(
        "image", metavar="IMAGE_OR_EXPORT_FILE", help="Docker image or exported file"
    )
    utils.add_core_image_arg(parser)
    parser.add_argument("--auth", metavar="USER:PASSWORD", help="Dhis2 instance authentication")
    parser.add_argument(
        "-d", "--detach", action="store_true", help="Run containers on the background"
    )
    parser.add_argument(
        "-k", "--keep-containers", action="store_true", help="Keep existing containers"
    )
    parser.add_argument("--tomcat-server-xml", metavar="FILE", help=server_xml_help)
    parser.add_argument("--dhis-conf", metavar="FILE", help=dhis_conf_help)
    parser.add_argument("--run-sql", metavar="DIRECTORY", help="Run .sql[.gz] files in directory")
    parser.add_argument("--db-port", metavar="PORT", help="Export DB Postgres port")
    parser.add_argument(
        "--run-scripts",
        metavar="DIRECTORY",
        help="Run shell scripts in folder (PRE-Tomcat; if filename ~ '^post' -> POST-Tomcat)",
    )
    parser.add_argument("--pull", action="store_true", help="Force a pull from docker hub")
    parser.add_argument("-p", "--port", type=int, metavar="N", help="Set Dhis2 instance port")
    parser.add_argument("--bind-ip", type=str, metavar="IP", help="Bind Dhis2 instance to IP")
    parser.add_argument("--deploy-path", type=str, help="Set Tomcat context.path")
    parser.add_argument("--java-opts", type=str, help="Set Tomcat JAVA_OPTS")
    parser.add_argument("--postgis-version", type=str, help="Set PostGIS database version")


def run(args):
    image_or_file = args.image

    if os.path.exists(image_or_file) and os.path.isfile(image_or_file):
        image2 = import_from_file(image_or_file)
    else:
        image2 = args.image

    args.image = image2
    start(args)


def import_from_file(images_path):
    dhis2_data_image_re = "/{}:".format(utils.DHIS2_DATA_IMAGE)
    result = utils.load_images_file(images_path)
    lines = result.stdout.decode("utf-8").splitlines()
    lines_splitted = [line.split() for line in lines]
    dhis2_data_images = [
        parts[-1] for parts in lines_splitted if parts and re.search(dhis2_data_image_re, parts[-1])
    ]
    if dhis2_data_images:
        return dhis2_data_images[0]
    else:
        msg = "Cannot find dhis2 data image (pattern={})".format(dhis2_data_image_re)
        raise utils.D2DockerError(msg)


def start(args):
    image_name = args.image
    utils.logger.info("Start image: {}".format(image_name))
    result = utils.get_image_status(image_name)
    if result["state"] == "running":
        msg = "Container already runnning for image {}".format(result["containers"]["db"])
        raise utils.D2DockerError(msg)
    port = args.port or utils.get_free_port()
    utils.logger.info("Port: {}".format(port))
    core_image = args.core_image
    override_containers = not args.keep_containers

    if args.pull:
        utils.run_docker_compose(["pull"], image_name, core_image=core_image)

    if override_containers:
        utils.run_docker_compose(["down", "--volumes"], image_name, core_image=core_image)

    up_args = filter(
        bool, ["--force-recreate" if override_containers else None, "-d" if args.detach else None]
    )

    deploy_path = "/" + re.sub("^/*", "", args.deploy_path) if args.deploy_path else ""

    with utils.stop_docker_on_interrupt(image_name, core_image):
        utils.run_docker_compose(
            ["up", *up_args],
            image_name,
            port=port,
            bind_ip=args.bind_ip,
            core_image=core_image,
            load_from_data=override_containers,
            post_sql_dir=args.run_sql,
            db_port=args.db_port,
            scripts_dir=args.run_scripts,
            deploy_path=deploy_path,
            dhis2_auth=args.auth,
            tomcat_server=args.tomcat_server_xml,
            dhis_conf=args.dhis_conf,
            java_opts=args.java_opts,
            postgis_version=args.postgis_version,
        )

    if args.detach:
        utils.logger.info("Detaching... run d2-docker logs to see logs")
