#!/bin/python
import os
import socket
import subprocess

from contextlib import closing

from . import consts


def get_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))  # pylint: disable=no-member
        return s.getsockname()[1]  # pylint: disable=no-member


def mkdir(path, safe=True):
    if safe and os.path.exists(path):
        raise OSError("Dir exists")
    os.makedirs(path)


def rmdir(path):
    try:
        os.removedirs(path)
    except PermissionError:
        pass


def remove(path):
    try:
        os.remove(path)
    except (PermissionError, FileNotFoundError):
        pass


def overlay_mount_with_name(name, image):
    overlay_mount(os.path.join(consts.IMAGE_DIR, image), os.path.join(consts.MACHINE_DIR, name), os.path.join(consts.WORK_DIR, name), os.path.join(consts.SYSTEMD_MOUNTPOINT, name))


def overlay_unmount_with_name(name):
    overlay_unmount(os.path.join(consts.SYSTEMD_MOUNTPOINT, name))


def overlay_mount(lowerdir, upperdir, workdir, mountpoint):
    [lower, upper, work, mnt] = map(lambda x: os.path.abspath(
        x), [lowerdir, upperdir, workdir, mountpoint])
    subprocess.run(["mount", "-t", "overlay", "overlay", "-o",
                    f"lowerdir={lower},upperdir={upper},workdir={work}", mnt])


def overlay_unmount(mountpoint):
    subprocess.run(["umount", mountpoint])


def container_boot(rootdir):
    subprocess.run(["systemd-nspawn", "-b", "-D", rootdir])


def os_install(rootdir, ostype):
    if ostype == "arch":
        subprocess.run(["pacstrap", "-c", "-i", rootdir, "base",
                        "base-devel", "openssh", "--ignore", "linux,linux-firmware"])
        if not os.path.exists(os.path.join(rootdir, "bin/sudo")):
            raise OSError("OS installation failed")
    else:
        raise ValueError("OS type not supported")


def post_os_install(rootdir):
    subprocess.run(["systemd-nspawn", "-D", rootdir,
                    "systemctl", "enable", "systemd-networkd"])
    with open(os.path.join(rootdir, "etc/securetty"), mode="a") as f:
        f.write("pts/0")
    with open(os.path.join(rootdir, "etc/ssh/sshd_config"), mode="a") as f:
        f.write("PermitRootLogin yes")


def change_pass(rootdir, username, passwd):
    subprocess.run(["chpasswd", "-R", rootdir],
                   input=f"{username}:{passwd}".encode("utf-8"))
