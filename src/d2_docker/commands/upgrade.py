import glob
import os

from d2_docker import utils, iter_versions

DESCRIPTION = "Upgrade DHIS2 version on core+data containers/images"


def setup(parser):
    parser.add_argument("--core-image-suffix", metavar="IMAGE", help="Image core name suffix")

    parser.add_argument("--from-version", metavar="VERSION", help="Source DHIS2 version")
    parser.add_argument("--to-version", metavar="VERSION", help="Destination DHIS2 version")

    parser.add_argument("--from", dest="from_", metavar="IMAGE", required=True, help="Source image")
    parser.add_argument("--to", metavar="IMAGE", required=True, help="Destination image data name")

    parser.add_argument("-r", "--keep-running", action="store_true", help="Keep last image running")

    parser.add_argument(
        "--migrations",
        dest="migrations_dir",
        metavar="DIRECTORY",
        help="Directory with migration scripts",
    )

    parser.add_argument("-p", "--port", type=int, metavar="N", help="DHIS2 instance port")


def run(args):
    source_image = utils.ImageName.from_string(args.from_)
    dest_image = utils.ImageName.from_string(args.to)
    from_version = args.from_version or source_image.version
    to_version = args.to_version or dest_image.version
    versions = iter_versions(from_version, to_version)
    utils.logger.info("Upgrade versions: {}".format(" -> ".join(versions)))

    for version in versions[1:]:
        dest_image_with_version = dest_image.with_version(version)
        core_image = dest_image_with_version.core().with_name(args.core_image_suffix).get()
        keep_running = args.keep_running and version == versions[-1]
        upgrade_to_version(
            migrations_dir=args.migrations_dir,
            version=version,
            core_image=core_image,
            source_image=source_image.get(),
            dest_image=dest_image_with_version.get(),
            port=args.port,
            keep_running=keep_running,
        )
        source_image = source_image.with_version(version)

    utils.logger.info("Done")


def upgrade_to_version(
    *, version, source_image, dest_image, core_image, port, migrations_dir, keep_running
):
    utils.logger.info("Upgrade: {} -> {}".format(source_image, dest_image))
    version_path = os.path.join(migrations_dir, version) if migrations_dir else None

    # Create core image
    dhis_war_path = os.path.join(version_path, "dhis.war") if version_path else None
    dhis2_home_paths = (
        glob.glob(os.path.join(version_path, "dhis2-home", "*")) if version_path else []
    )
    war_exists = dhis_war_path and os.path.exists(dhis_war_path)
    create_core_kwargs = dict(war=dhis_war_path) if war_exists else dict(version=version)
    core_docker_dir = utils.get_docker_directory("core")
    utils.create_core(
        docker_dir=core_docker_dir,
        image=core_image,
        dhis2_home_paths=dhis2_home_paths,
        **create_core_kwargs
    )

    # Create data image
    data_docker_dir = utils.get_docker_directory("data")
    utils.copy_image(data_docker_dir, source_image, dest_image)

    # Start
    final_port = port or utils.get_free_port()

    utils.run_docker_compose(["down", "--volumes"], dest_image, core_image=core_image)

    with utils.stop_docker_on_interrupt(dest_image, core_image):
        utils.run_docker_compose(
            ["up", "--force-recreate", "-d"],
            dest_image,
            port=final_port,
            core_image=core_image,
            load_from_data=True,
            post_sql_dir=version_path,
            scripts_dir=version_path,
        )

        if not utils.wait_for_server(final_port):
            raise utils.D2DockerError("Error waiting for DHIS2 instance to be active")

        # Commit
        utils.build_image_from_source(data_docker_dir, dest_image, dest_image)

    # Stop
    if not keep_running:
        utils.run_docker_compose(["stop"], dest_image)
