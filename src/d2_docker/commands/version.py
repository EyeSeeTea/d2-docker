from d2_docker import utils
import pkg_resources  # part of setuptools

DESCRIPTION = "Show version"


def setup(parser):
    pass


def run(args):
    utils.run(["docker", "-v"])
    utils.run(["docker-compose", "-v"])
    resource = pkg_resources.require("d2-docker")
    if resource:
        version = pkg_resources.require("d2-docker")[0].version
        print("d2-docker version {}".format(version))
    else:
        print("Cannot get d2-docker version")

