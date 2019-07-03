#!/bin/python
import os
import shutil
import subprocess

from slugify import slugify

from . import consts
from . import utils
from .template import Template

# TODO implement custom containers (as plugins?)


class Container(object):
    def __init__(self, name, image):
        self._name = ""
        self._password = ""
        self._created = False
        self.port = -1
        self._image = image
        self.name = slugify(name, word_boundary=True, separator='-')

    @property
    def image(self):
        return self._image

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        if self._created:
            if not os.path.ismount(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name)):
                utils.overlay_mount_with_name(self.name, self._image)
                utils.change_pass(os.path.join(
                    consts.SYSTEMD_MOUNTPOINT, self.name), "root", value)
                utils.overlay_unmount_with_name(self.name)
            else:
                utils.change_pass(os.path.join(
                    consts.SYSTEMD_MOUNTPOINT, self.name), "root", value)
        self._password = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if os.path.exists(os.path.join(consts.MACHINE_DIR, value)):
            raise OSError(f"Container {value} exists.")
        if self._created:
            raise RuntimeError(
                "Cannot rename container when it has already been built.")
        self._name = value

    def start(self, lazy=True):
        if self._created:
            # Mount container if not mounted
            if not os.path.ismount(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name)):
                utils.overlay_mount_with_name(self.name, self._image)

            # Start socket unit
            subprocess.run(
                ["systemctl", "start", f"container_{self.name}.socket"])
            if not lazy:
                # Start service unit
                subprocess.run(
                    ["systemctl", "start", f"container_{self.name}.service"])
        else:
            raise OSError("Container hasn't been built.")

    def build(self):
        # TODO move build func to inherited classes (eg. ArchContainer, DebianContainer)
        # Init template instance
        templates = Template()

        # Throw out an exception if container already exists
        if self._created:
            raise KeyError(f"Container {self.name} is already built")
        elif not self._name:
            raise KeyError("Empty name isn't allowed.")
        elif not self._password:
            raise KeyError("Empty password isn't allowed.")

        # Create rootfs, overlay workdir and mountpoint
        os.makedirs(os.path.join(consts.MACHINE_DIR, self.name))
        os.makedirs(os.path.join(consts.WORK_DIR, self.name))
        os.makedirs(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name))

        # Assign a free port to our new container
        self.port = utils.get_free_port()
        utils.get_free_port()

        # Generate essential systemd configs
        with open(os.path.join(consts.SYSTEMD_NSPAWN_DIR, f"{self.name}.nspawn"), mode="w") as f:
            f.write(templates.nspawn.substitute(port=self.port))
        with open(os.path.join(consts.SYSTEMD_UNIT_DIR, f"container_{self.name}.service"), mode="w") as f:
            f.write(templates.container_service.substitute(name=self.name))
        with open(os.path.join(consts.SYSTEMD_UNIT_DIR, f"container_{self.name}.socket"), mode="w") as f:
            f.write(templates.container_socket.substitute(
                name=self.name, port=self.port))

        # Restart systemd daemon to apply changes
        subprocess.run(["systemctl", "daemon-reload"])

        # Mount the container first
        utils.overlay_mount_with_name(self.name, self._image)

        # Write port number to guest os
        with open(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name, consts.SYSTEMD_UNIT_DIR[1:], "sshd-alter.socket"), mode="w") as f:
            f.write(templates.sshd_socket.substitute(port=self.port))
        with open(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name, consts.SYSTEMD_UNIT_DIR[1:], "sshd-alter@.service"), mode="w") as f:
            f.write(templates.sshd_service)

        # Enable sshd unit and socket
        subprocess.run(["systemd-nspawn", "-D", os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name), "ln", "-s", os.path.join(
            consts.SYSTEMD_UNIT_DIR, "sshd-alter.socket"), os.path.join(consts.SYSTEMD_UNIT_DIR, "socket.target.wants")])
        utils.change_pass(os.path.join(
            consts.SYSTEMD_MOUNTPOINT, self.name), "root", self._password)

        # Clean up
        utils.overlay_unmount_with_name(self.name)
        self._created = True

    def destroy(self):
        if not self._created:
            raise KeyError("Container hasn't been built.")

        # Shutdown container
        subprocess.run(["systemctl", "stop", f"container_{self.name}.socket"])
        subprocess.run(
            ["systemctl", "stop", f"container_{self.name}.service"])

        # Unmount overlay fs
        utils.overlay_unmount_with_name(self.name)

        # Delete rootfs
        shutil.rmtree(os.path.join(consts.MACHINE_DIR,
                                   self.name), ignore_errors=True)
        shutil.rmtree(os.path.join(consts.WORK_DIR,
                                   self.name), ignore_errors=True)

        # Delete mountpoint
        utils.rmdir(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name))

        # Delete systemd configs
        os.remove(os.path.join(
            consts.SYSTEMD_NSPAWN_DIR, f"{self.name}.nspawn"))
        os.remove(os.path.join(consts.SYSTEMD_UNIT_DIR,
                               f"container_{self.name}.service"))
        os.remove(os.path.join(consts.SYSTEMD_UNIT_DIR,
                               f"container_{self.name}.socket"))

        # Reload systemd daemon to apply changes
        subprocess.run(["systemctl", "daemon-reload"])

        self._created = False

    def mount(self):
        if not self._created:
            raise KeyError(f"Container {self.name} doesn't exist.")
            return
        if os.path.ismount(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name)):
            raise OSError(f"Container {self.name} is mounted.")
            return
        utils.overlay_mount_with_name(self.name, self._image)

    def umount(self):
        if not self._created:
            raise KeyError(f"Container {self.name} doesn't exist.")
            return
        if not os.path.ismount(os.path.join(consts.SYSTEMD_MOUNTPOINT, self.name)):
            raise OSError(f"Container {self.name} isn't mounted.")
            return
        utils.overlay_unmount_with_name(self.name)


    def stop(self, grace=False):
        if self._created:
            # Stop socket unit
            subprocess.run(
                ["systemctl", "stop", f"container_{self.name}.socket"])
            if not grace:
                # Stop service unit
                subprocess.run(
                    ["systemctl", "stop", f"container_{self.name}.service"])
                # Umount overlay fs
                utils.overlay_unmount_with_name(self.name)
        else:
            raise OSError("Container hasn't been built.")
