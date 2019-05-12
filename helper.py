#!/bin/python
import os
import click
import subprocess

@click.group()
def cli():
    pass

@click.group()
def overlay():
    pass

@click.group()
def container():
    pass

@overlay.command("mount")
@click.argument('lowerdir')
@click.argument('upperdir')
@click.argument('workdir')
@click.argument('mountpoint')
def overlay_mount(lowerdir, upperdir, workdir, mountpoint):
    [lower, upper, work, mnt] = map(lambda x: os.path.abspath(x), [lowerdir, upperdir, workdir, mountpoint])
    subprocess.run(["mount", "-t", "overlay", "overlay", "-o", f"lowerdir={lower},upperdir={upper},workdir={work}", mnt])

@overlay.command("unmount")
@click.argument('mountpoint')
def overlay_unmount(mountpoint):
    subprocess.run(["umount", mountpoint])

@container.command("boot")
@click.argument('rootdir')
def container_boot(rootdir):
    subprocess.run(["systemd-nspawn", "-b", "-D", rootdir])

cli.add_command(overlay)
cli.add_command(container)

if __name__ == "__main__":
    cli()
