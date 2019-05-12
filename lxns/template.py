import os
from string import Template as _Template


class Template:
    def __init__(self):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates/default.nspawn")) as f:
            self.nspawn = _Template(f.read())
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates/sshd.socket")) as f:
            self.sshd_socket = _Template(f.read())
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates/sshd@.service")) as f:
            self.sshd_service = f.read()
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates/container-default.service")) as f:
            self.container_service = _Template(f.read())
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates/container-default.socket")) as f:
            self.container_socket = _Template(f.read())
