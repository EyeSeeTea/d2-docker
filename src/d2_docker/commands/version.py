import pkg_resources  # part of setuptools
import re
from d2_docker import utils

DESCRIPTION = "Show version"


def setup(_parser):
    pass


def run(_args):
    utils.run(["docker", "-v"])
    utils.run(["docker-compose", "-v"])
    d2_docker = get_d2_docker_version()
    if d2_docker:
        print("d2-docker version {}".format(d2_docker))
    else:
        print("Cannot get d2-docker version")


def get_field(command, field_index):
    lines = utils.run(command, capture_output=True).stdout.splitlines()
    if not lines:
        return
    line = lines[0]
    fields = line.split()
    if len(fields) > field_index:
        word = fields[field_index].decode("utf-8")
        return re.sub("[,]", "", word)


def get_versions():
    docker = get_field(["docker", "-v"], 2)
    docker_compose = get_field(["docker-compose", "-v"], 3)
    d2_docker = get_d2_docker_version()
    return dict({"docker": docker, "docker-compose": docker_compose, "d2-docker": d2_docker})


def get_d2_docker_version():
    resources = pkg_resources.require("d2-docker")
    return resources[0].version if resources else None
