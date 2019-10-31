import gzip
import os
import re

from d2_docker import utils

DESCRIPTION = "Export d2-docker images to a single file"


def setup(parser):
    utils.add_image_arg(parser)
    utils.add_core_image_arg(parser)
    parser.add_argument("output_file", metavar="TGZ_PATH", type=str, help="Output tar.gz file")


def run(args):
    image_name = args.image or utils.get_running_image_name()
    core = args.core_image
    result = utils.run_docker_compose(["config"], image_name, core_image=core, capture_output=True)
    yaml_contents = result.stdout.decode("utf-8")

    # Use regexp instead of using a third-party YAML parser to ease deployment on Windows.
    image_names = re.findall(r"image: (\S+)\r?$", yaml_contents, re.MULTILINE)
    utils.logger.info("Export images: {}".format(", ".join(image_names)))
    tar_file = args.output_file + ".tar"
    utils.save_images(image_names, tar_file)
    compress_tar(tar_file, args.output_file)


def compress_tar(input_path, output_path):
    gzip_file(input_path, output_path)
    os.remove(input_path)
    utils.logger.info("Compressed output file: {}".format(output_path))


def gzip_file(input_path, output_path):
    with open(input_path, "rb") as fd_in:
        with gzip.open(output_path, "wb") as fd_out:
            fd_out.writelines(fd_in)
