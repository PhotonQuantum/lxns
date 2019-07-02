#!/bin/python
import os
import subprocess
import pickle
import getpass
from functools import wraps

import fire
from loguru import logger

import utils
from template import Template
from container import Container

templates = Template()

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
        if not os.path.exists("index.pickle"):
            self._containers = []
        else:
            with open("index.pickle", "rb") as f:
                self._containers = pickle.load(f)

    def __del__(self):
        with open("index.pickle", "wb") as f:
            pickle.dump(self._containers, f, protocol=pickle.HIGHEST_PROTOCOL)

    @root
    def create(self, name):
        container = Container(name)
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


def main():
    fire.Fire(entrypoint, name="lxns")

if __name__ == "__main__":
    main()
