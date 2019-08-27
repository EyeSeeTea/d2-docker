import logging

import utils

DESCRIPTION = "List d2-docker data images"
NAME = "list"


def setup(parser):
    pass


def run(args):
    pattern = "dhis2-db"
    logging.info("Listing docker images with pattern: {}".format(pattern))
    cmd = ["docker", "image", "ls", "--format={{.Repository}} {{.Tag}}"]
    result = utils.run(cmd, capture_output=True)
    lines_parts = [line.split() for line in result.stdout.decode("utf-8").splitlines()]
    data_image_names = [
        "{}:{}".format(parts[0], parts[1]) for parts in lines_parts if pattern in parts[0]
    ]
    print("\n".join(sorted(set(data_image_names))))
