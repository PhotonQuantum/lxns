#!/bin/python
import os

BASE_DIR = "/etc/lxns"
VAR_DIR = "/var/lib/lxns"

CONTAINER_DIR = os.path.join(BASE_DIR, "containers")
MACHINE_DIR = os.path.join(CONTAINER_DIR, "machines")
WORK_DIR = os.path.join(CONTAINER_DIR, "workdirs")

IMAGE_DIR = os.path.join(BASE_DIR, "images")

SYSTEMD_NSPAWN_DIR = "/etc/systemd/nspawn"
SYSTEMD_UNIT_DIR = "/etc/systemd/system"
SYSTEMD_MOUNTPOINT = "/var/lib/machines"

CONTAINER_INDEX = os.path.join(VAR_DIR, "containers.pickle")
