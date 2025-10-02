import atexit
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from d2_docker import utils

GLOWROOT_DEFAULT_PORT = "4000"

def get_latest_glowroot_url():
    glowroot_releases_url = "https://api.github.com/repos/glowroot/glowroot/releases/latest"
    glowroot_download_url = "https://github.com/glowroot/glowroot/releases/download"
    with urllib.request.urlopen(glowroot_releases_url) as response:
        data = response.read().decode()
        release_info = json.loads(data)

    tag_name = release_info["tag_name"]
    return "{}/{}/glowroot-{}-dist.zip".format(glowroot_download_url, tag_name, tag_name.lstrip("v"))

def get_glowroot_zip(command, glowroot_zip, glowroot):
    logger = utils.logger
    glowroot_path=None
    if isinstance(command, list) and command[0] == "up":
        glowroot_file = tempfile.NamedTemporaryFile(delete=False, prefix="glowroot_", suffix=".zip", dir="/tmp")
        glowroot_path = glowroot_file.name

        atexit.register(lambda: os.remove(glowroot_path) if os.path.exists(glowroot_path) else None)
        if glowroot_zip:
            logger.debug("Copy zip file: {} -> {}".format(glowroot_zip, glowroot_path))
            shutil.copy(glowroot_zip, glowroot_path)
        elif glowroot:
            glowroot_url = get_latest_glowroot_url()
            logger.info("Download file: {}".format(glowroot_url))
            urllib.request.urlretrieve(glowroot_url, glowroot_path)
        else:
            # empty zipfile
            with zipfile.ZipFile(glowroot_path, mode="w") as zf:
                pass

    return utils.get_absfile_for_docker_volume(glowroot_path)

def get_port_glowroot(glowroot_port, glowroot_zip, glowroot):
    port = glowroot_port if glowroot_port else GLOWROOT_DEFAULT_PORT
    return "{}:{}".format(port, GLOWROOT_DEFAULT_PORT) if (glowroot_port or glowroot_zip or glowroot) else None
