#!/bin/python
import click
import os
import re
import shutil
import utils
import subprocess
from slugify import slugify
from template import Template
from loguru import logger


templates = Template()


def check_root():
    if os.getenv("SUDO_UID") is None:
        logger.error("Root privileges required.")
        return False
    else:
        return True


@click.group()
def cli():
    pass


@click.group()
def container():
    pass


@click.command("init")
@logger.catch
def init_all():
    if not check_root():
        return
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


@container.command("create")
@click.argument("name")
@click.argument("password")
@logger.catch
def container_create(name, password):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    logger.info(f"Creating container {clean_name} ...")
    if os.path.exists(f"containers/machines/{clean_name}"):
        logger.error(f"Container {clean_name} already exists")
        return
    os.makedirs(f"containers/machines/{clean_name}")
    os.makedirs(f"containers/workdirs/{clean_name}")
    os.makedirs(f"/var/lib/machines/{clean_name}")
    logger.info("Allocating SSH port...")
    port = utils.get_free_port()
    logger.info("Creating nspawn file...")
    with open(f"/etc/systemd/nspawn/{clean_name}.nspawn", mode="w") as f:
        f.write(templates.nspawn.substitute(port=port))
    logger.info("Creating systemd service...")
    with open(f"/etc/systemd/system/container_{clean_name}.service", mode="w") as f:
        f.write(templates.container_service.substitute(name=clean_name))
    with open(f"/etc/systemd/system/container_{clean_name}.socket", mode="w") as f:
        f.write(templates.container_socket.substitute(
            name=clean_name, port=port))
    logger.info("Reloading systemd daemon...")
    subprocess.run(["systemctl", "daemon-reload"])
    logger.info("Configuring container...")
    utils.overlay_mount_with_name(clean_name)
    with open(f"/var/lib/machines/{clean_name}/etc/systemd/system/sshd-alter.socket", mode="w") as f:
        f.write(templates.sshd_socket.substitute(port=port))
    with open(f"/var/lib/machines/{clean_name}/etc/systemd/system/sshd-alter@.service", mode="w") as f:
        f.write(templates.sshd_service)
    subprocess.run(["systemd-nspawn", "-D", f"/var/lib/machines/{clean_name}", "ln", "-s",
                    "/etc/systemd/system/sshd-alter.socket", "/etc/systemd/system/sockets.target.wants"])
    utils.change_pass(f"/var/lib/machines/{clean_name}", "root", password)
    utils.overlay_unmount_with_name(clean_name)
    logger.success(f"Container {clean_name} created.")


@container.command("destroy")
@click.argument("name")
def container_destroy(name):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    if not os.path.exists(f"containers/machines/{clean_name}"):
        logger.error(f"Container {clean_name} doesn't exist.")
        return
    print("\033[33;5;7m!!! WARNING: THIS OPERATION CANNOT BE REVERTED !!!\033[0m")
    confirm1 = click.confirm(
        f"\033[33;5;7m!!! Do you want to destroyed container {clean_name}?\033[0m")
    if confirm1:
        confirm2 = click.prompt(
            "\033[33;5;7mYes, I REALLY know what I'm doing, please DESTROY container ...\033[0m [TYPE YOUR CONTAINER NAME AGAIN]") == clean_name
    if confirm1 and confirm2:
        logger.info(f"Destroying container {clean_name}")
        logger.info("Shutting down container...")
        subprocess.run(
            ["systemctl", "stop", f"container_{clean_name}.service"])
        subprocess.run(["systemctl", "stop", f"container_{clean_name}.socket"])
        logger.info("Unmounting overlayfs...")
        utils.overlay_unmount_with_name(clean_name)
        logger.info("Deleting container fs layer...")
        shutil.rmtree(f"containers/machines/{clean_name}", ignore_errors=True)
        shutil.rmtree(f"containers/workdirs/{clean_name}", ignore_errors=True)
        logger.info("Removing mountpoint...")
        utils.rmdir(f"/var/lib/machines/{clean_name}")
        logger.info("Deleting nspawn file...")
        os.remove(f"/etc/systemd/nspawn/{clean_name}.nspawn")
        logger.info("Deleting systemd service...")
        os.remove(f"/etc/systemd/system/container_{clean_name}.service")
        os.remove(f"/etc/systemd/system/container_{clean_name}.socket")
        logger.info("Reloading systemd daemon...")
        subprocess.run(["systemctl", "daemon-reload"])
        logger.success(
            f"Container {clean_name} destroyed. Some files may still exist.")
    else:
        logger.error("Process aborted.")


@container.command("mount")
@click.argument("name")
def container_mount(name):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    if not os.path.exists(f"containers/machines/{clean_name}"):
        logger.error(f"Container {clean_name} doesn't exist.")
        return
    if os.path.ismount(f"/var/lib/machines/{clean_name}"):
        logger.error(f"Container {clean_name} already mounted.")
        return
    utils.overlay_mount_with_name(clean_name)
    logger.success(f"Container {clean_name} mounted.")


@container.command("unmount")
@click.argument("name")
def container_unmount(name):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    if not os.path.exists(f"containers/machines/{clean_name}"):
        logger.error(f"Container {clean_name} doesn't exist.")
        return
    if not os.path.ismount(f"/var/lib/machines/{clean_name}"):
        logger.error(f"Container {clean_name} not mounted.")
        return
    utils.overlay_unmount_with_name(clean_name)
    logger.success(f"Container {clean_name} unmounted.")


@container.command("info")
@click.argument("name")
def container_info(name):
    clean_name = slugify(name, word_boundary=True, separator="-")
    if not os.path.exists(f"containers/machines/{clean_name}"):
        logger.error(f"Container {clean_name} doesn't exist.")
        return
    machine_path = os.path.abspath(f"containers/machines/{clean_name}")
    workdir_path = os.path.abspath(f"containers/workdirs/{clean_name}")
    with open(f"/etc/systemd/nspawn/{clean_name}.nspawn") as f:
        nspawn_content = f.read()
    port = re.findall("(?<=Port=)\d*", nspawn_content)[0]  # noqa
    logger.success(f"Container {clean_name} info got.")
    msg = f"Name: {clean_name}\n"
    msg += f"Machine Path: {machine_path}\n"
    msg += f"Workdir Path: {workdir_path}\n"
    msg += f"Mountpoint: /var/lib/machines/{clean_name}\n"
    msg += f"Nspawn config: /etc/systemd/nspawn/{clean_name}.nspawn\n"
    msg += f"SSH Port: {port}"
    print(msg)


@container.command("passwd")
@click.argument("name")
def container_passwd(name):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    if not os.path.exists(f"containers/machines/{clean_name}"):
        logger.error(f"Container {clean_name} doesn't exist.")
        return
    if not os.path.ismount(f"/var/lib/machines/{clean_name}"):
        logger.error(f"Container {clean_name} isn't mounted.")
        return
    passwd = click.prompt("New password", hide_input=True)
    if passwd != click.prompt("Retype new password", hide_input=True):
        logger.error("Passwords doesn't match.")
        return
    utils.change_pass(f"/var/lib/machines/{clean_name}", "root", passwd)
    logger.success("Password updated successfully.")


@container.command("enable")
@click.argument("name")
def container_enable(name):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    if not os.path.ismount(f"/var/lib/machines/{clean_name}"):
        logger.info(f"Container {clean_name} not mounted. Mounting...")
        utils.overlay_mount_with_name(clean_name)
    subprocess.run(["systemctl", "start", f"container_{clean_name}.socket"])
    with open(f"/etc/systemd/nspawn/{clean_name}.nspawn") as f:
        nspawn_content = f.read()
    port = re.findall("(?<=Port=)\d*", nspawn_content)[0]  # noqa
    logger.success(
        f"Container {clean_name} is ready to be activated at port {port}.")


@container.command("disable")
@click.argument("name")
def container_disable(name):
    if os.getenv("SUDO_UID") is None:
        logger.error("Root privileges required.")
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    subprocess.run(["systemctl", "stop", f"container_{clean_name}.socket"])
    with open(f"/etc/systemd/nspawn/{clean_name}.nspawn") as f:
        nspawn_content = f.read()
    port = re.findall("(?<=Port=)\d*", nspawn_content)[0]  # noqa
    logger.success(
        f"Container {clean_name} stops handling new connections from port {port}.")


@container.command("start")
@click.argument("name")
def container_start(name):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    if not os.path.ismount(f"/var/lib/machines/{clean_name}"):
        logger.info(f"Container {clean_name} not mounted. Mounting...")
        utils.overlay_mount_with_name(clean_name)
    subprocess.run(["systemctl", "start", f"container_{clean_name}.service"])
    logger.success(f"Container {clean_name} started.")


@container.command("stop")
@click.argument("name")
def container_stop(name):
    if not check_root():
        return
    clean_name = slugify(name, word_boundary=True, separator="-")
    subprocess.run(["systemctl", "stop", f"container_{clean_name}.service"])
    logger.success(f"Container {clean_name} stopped.")


@container.command("all")
@click.argument("operation")
@click.pass_context
def container_all(ctx, operation):
    if operation == "ls":
        print("Available containers:")
        print(*os.listdir("containers/machines"))
    else:
        try:
            operator = globals()[f"container_{operation}"]
        except KeyError:
            logger.error("Unknown operation.")
            return
        for machine in os.listdir("containers/machines"):
            ctx.invoke(operator, name=machine)
        logger.success("Batch operation finished.")


cli.add_command(init_all)
cli.add_command(container)
if __name__ == "__main__":
    cli()
