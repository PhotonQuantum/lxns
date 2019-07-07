#!/bin/python
import tarfile
import getpass
import os
import pickle
import shutil
import subprocess
from functools import wraps

import fire
from loguru import logger
from slugify import slugify
import prettytable

from . import consts
from . import utils
from .container import Container

# TODO plugin system

# TODO refract init func
@logger.catch
def init_all():
    logger.info("Creating dirs...")
    os.makedirs("containers")
    os.makedirs("containers/base/arch")
    os.makedirs("containers/workdirs")
    os.makedirs("containers/machines")
    try:
        os.makedirs("/etc/systemd/nspawn")
    except FileExistsError:
        pass
    logger.info("Changing IP Forwarding settings...")
    try:
        os.makedirs("/etc/sysctl.d")
    except FileExistsError:
        pass
    if not os.path.exists("/etc/sysctl.d/30-ip-forward.conf"):
        with open("/etc/sysctl.d/30-ip-forward.conf", mode="w") as f:
            f.write("net.ipv4.ip_forward=1")
    subprocess.run(["sysctl", "-p", "/etc/sysctl.d/30-ip-forward.conf"])
    logger.info("Installing OS...")
    utils.os_install("containers/base/arch", "arch")
    utils.post_os_install("containers/base/arch")
    logger.success("Init finished.")


def root(func):
    @wraps(func)
    def root_func(*args, **kwargs):
        if os.getenv("SUDO_UID") is None:
            logger.critical("Root required.")
        else:
            return func(*args, **kwargs)
    return root_func


class entrypoint(object):

    def __init__(self):
        # TODO save/load through plugins

        # Load container list
        if not os.path.exists(consts.CONTAINER_INDEX):
            self._containers = []
        else:
            with open(consts.CONTAINER_INDEX, "rb") as f:
                self._containers = pickle.load(f)

        # Warn user if not root user
        if os.getenv("SUDO_UID") is None:
            logger.warning("Not root user. Read-only Mode.")

    def __del__(self):
        # Save container list
        if not os.getenv("SUDO_UID") is None:
            with open(consts.CONTAINER_INDEX, "wb") as f:
                pickle.dump(self._containers, f, protocol=pickle.HIGHEST_PROTOCOL)

    @root
    def create(self, name, image):
        if not os.path.exists(os.path.join(consts.IMAGE_DIR, image)):
            logger.error("Image not found.")
            return
        container = Container(name, image)
        container.password = getpass.getpass()
        container.build()
        self._containers.append(container)

    @root
    def destroy(self, name):
        container = next(
            filter(lambda x: x.name == name, self._containers), None)
        if container:
            container.destroy()
            self._containers.remove(container)
            logger.success("Container destroyed.")
        else:
            logger.error("Container not found.")

    @root
    def start(self, name, lazy=True):
        container = next(
            filter(lambda x: x.name == name, self._containers), None)
        if container:
            container.start(lazy)
            logger.success("Container started.")
        else:
            logger.error("Container not found.")

    @root
    def stop(self, name, grace=False):
        container = next(
            filter(lambda x: x.name == name, self._containers), None)
        if container:
            container.stop(grace)
            logger.success("Container stopped.")
        else:
            logger.error("Container not found.")

    def info(self, name):
        container = next(
            filter(lambda x: x.name == name, self._containers), None)
        if container:
            print(f"Name: {container.name}")
            print(f"Password: {container.password}")
            print(f"Port: {container.port}")
        else:
            logger.error("Container not found.")

    def status(self, name):
        container = next(
            filter(lambda x: x.name == name, self._containers), None)
        if container:
            subprocess.run(["machinectl", "status", container.name])
        else:
            logger.error("Container not found.")

    @root
    def stage_image(self, name, tar_file):
        _name = name
        name = slugify(name, word_boundary=True, separator="-")
        if name != _name:
            logger.warning(f"Image name changed to {name}.")
        if os.path.exists(os.path.join(consts.IMAGE_DIR, name)):
            logger.error("Image exists.")
            return
        os.makedirs(os.path.join(consts.IMAGE_DIR, name))
        print(f"Decompressing {tar_file} to image {name}")
        with tarfile.open(tar_file) as f:
            f.extractall(os.path.join(consts.IMAGE_DIR, name))
        print("Image staged.")

    @root
    def unstage_image(self, name):
        if not os.path.exists(os.path.join(consts.IMAGE_DIR, name)):
            logger.error("Image doesn't exist.")
            return
        elif name in map(lambda x: x.image, self._containers):
            logger.error("Image is in use.")
            print("Image is used by the following containers:")
            print(*list(map(lambda x: x.name, filter(
                lambda x: x.image == name, self._containers))), sep="\n")
            return
        print("Deleting image")
        shutil.rmtree(os.path.join(consts.IMAGE_DIR, name))
        print("Image unstaged.")

    def list_containers(self):
        table = prettytable.PrettyTable()
        table.field_names = ["Name", "Port"]
        for container in self._containers:
            table.add_row([container.name, container.port])
        print(table)

def main():
    fire.Fire(entrypoint, name="lxns")


if __name__ == "__main__":
    main()
