#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from typing import Callable, NamedTuple, Tuple

pwd = os.path.realpath(os.path.dirname(__file__))

# define Sphinx-commands:
CMD_SPHINXBUILD = "sphinx-build"
CMD_SPHINXAPIDOC = "sphinx-apidoc"

# define directories:
SOURCEDIR = os.path.join(pwd, "source")
BUILDDIR = os.path.join(pwd, "build")


class MakeCommand(NamedTuple):
    """ Defines an available command that can be launched from this module."""

    command: str
    description: str
    python_target: Callable[[], None]
    depends_on: Tuple["MakeCommand", ...]


# Define Python target callables:
def fun_clean():
    """ Cleans the Sphinx build directory. """
    print_running_command(cmd=clean)
    if os.path.exists(BUILDDIR):
        shutil.rmtree(path=BUILDDIR)


def fun_html():
    """ Runs a Sphinx build for pytools generating HTML. """
    print_running_command(cmd=html)
    os.makedirs(BUILDDIR, exist_ok=True)
    sphinx_html_opts = ["-M html", quote_path(SOURCEDIR), quote_path(BUILDDIR)]
    subprocess.run(
        args=f"{CMD_SPHINXBUILD} {' '.join(sphinx_html_opts)}", shell=True, check=True
    )


# Define MakeCommands
clean = MakeCommand(
    command="clean",
    description=f"remove Sphinx build output in {BUILDDIR}",
    python_target=fun_clean,
    depends_on=(),
)
html = MakeCommand(
    command="html",
    description="build pytools Sphinx docs as HTML",
    python_target=fun_html,
    depends_on=(clean,),
)

available_cmds = (clean, html)


def run_make():
    """ Run this make script with the given arguments. """
    if len(sys.argv) < 2:
        print_usage()

    commands_passed = sys.argv[1:]

    # check all given commands:
    for selected_cmd in commands_passed:
        if selected_cmd not in {c.command for c in available_cmds}:
            print(f"Unknown build command: {selected_cmd}")
            print_usage()
            exit(1)

    # run all given commands:
    executed_commands = set()
    for selected_cmd in commands_passed:
        for known_cmd in available_cmds:
            if selected_cmd == known_cmd.command:
                for dependant_on_cmd in known_cmd.depends_on:
                    if dependant_on_cmd not in executed_commands:
                        dependant_on_cmd.python_target()

                known_cmd.python_target()
                executed_commands.add(known_cmd)


def quote_path(path: str) -> str:
    """ Quotes a filepath that contains spaces."""
    if " " in path:
        return '"' + path + '"'
    else:
        return path


def print_usage() -> None:
    # Define a help string to explain the usage:
    usage = """
    pytools docs build script
    =========================
    
    Available program arguments:
    """

    usage += "\n".join([f"\t{c.command} – {c.description}" for c in available_cmds])
    print(usage)


def print_running_command(cmd: MakeCommand) -> None:
    """ Prints info on a started command. """
    print(f"Running command {cmd.command} – {cmd.description}")


if __name__ == "__main__":
    run_make()
