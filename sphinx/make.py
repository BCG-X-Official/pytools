#!/usr/bin/env python3
"""
Sphinx documentation build script
"""

import os
import shutil
import subprocess
import sys
from typing import *

cwd = os.getcwd()

# define Sphinx-commands:
CMD_SPHINXBUILD = "sphinx-build"
CMD_SPHINXAPIDOC = "sphinx-apidoc"

# define directories:
# todo: check which ones are eventually obsolete
SKLEARNDF_SOURCEDIR = os.path.join(cwd, os.pardir, "src")
SOURCEDIR = os.path.join(cwd, "source")
AUXILIARYDIR = os.path.join(cwd, "auxiliary")
SOURCEAPIDIR = os.path.join(SOURCEDIR, "api")
BUILDDIR = os.path.join(cwd, "build")
TEMPLATEDIR = os.path.join(SOURCEDIR, "_templates")
SCRIPTSDIR = os.path.join(SOURCEDIR, "scripts")
TUTORIALDIR = os.path.join(SOURCEDIR, "tutorial")
NOTEBOOKDIR = os.path.join(SKLEARNDF_SOURCEDIR, os.pardir, "notebooks")
TUTORIALBUILD = os.path.join(SCRIPTSDIR, "transform_notebook.py")


class MakeCommand(NamedTuple):
    """ Defines an available command that can be launched from this module."""

    command: str
    description: str
    python_target: Callable[[], None]
    depends_on: Tuple["MakeCommand", ...]


# Define Python target callables:
def fun_clean() -> None:
    """
    Clean the Sphinx build directory.
    """
    print_running_command(cmd=clean)
    if os.path.exists(BUILDDIR):
        shutil.rmtree(path=BUILDDIR)


def fun_apidoc() -> None:
    """
    Run Sphinx apidoc.
    """
    print_running_command(cmd=apidoc)
    sphinxapidocopts = [
        "-e",
        f"-t {quote_path(TEMPLATEDIR)}",
        "--no-toc",
        f"-o {quote_path(SOURCEAPIDIR)}",
        "-f",
        quote_path(SKLEARNDF_SOURCEDIR),
    ]
    os.environ["SPHINX_APIDOC_OPTIONS"] = ",".join(["members", "undoc-members"])
    subprocess.run(
        args=f"{CMD_SPHINXAPIDOC} {' '.join(sphinxapidocopts)}", shell=True, check=True
    )


def fun_html() -> None:
    """
    Run a Sphinx build for generating HTML.
    """

    print_running_command(cmd=html)
    os.makedirs(BUILDDIR, exist_ok=True)
    sphinx_html_opts = ["-M html", quote_path(SOURCEDIR), quote_path(BUILDDIR)]
    subprocess.run(
        args=f"{CMD_SPHINXBUILD} {' '.join(sphinx_html_opts)}", shell=True, check=True
    )

    # create interactive versions of all notebooks

    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    # noinspection PyUnresolvedReferences
    from source.scripts.transform_notebook import docs_notebooks_to_interactive

    for notebook_source_dir in [TUTORIALDIR, AUXILIARYDIR]:
        if os.path.isdir(notebook_source_dir):
            docs_notebooks_to_interactive(notebook_source_dir, NOTEBOOKDIR)


# Define MakeCommands
clean = MakeCommand(
    command="clean",
    description=f"remove Sphinx build output in {BUILDDIR}",
    python_target=fun_clean,
    depends_on=(),
)
apidoc = MakeCommand(
    command="apidoc",
    description="generate Sphinx apidoc from sources.",
    python_target=fun_apidoc,
    depends_on=(clean,),
)
html = MakeCommand(
    command="html",
    description="build Sphinx docs as HTML",
    python_target=fun_html,
    depends_on=(clean,),
)

available_cmds = (clean, apidoc, html)


def run_make() -> None:
    """
    Run this make script with the given arguments.
    """
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
    """
    Print a help string to explain the usage of this script.
    """
    usage = """Sphinx documentation build script
=================================

Available program arguments:
"""

    usage += "\n".join([f"\t{c.command} – {c.description}" for c in available_cmds])

    print(usage)


def print_running_command(cmd: MakeCommand) -> None:
    """ Prints info on a started command. """
    print(f"Running command {cmd.command} – {cmd.description}")


if __name__ == "__main__":
    run_make()
