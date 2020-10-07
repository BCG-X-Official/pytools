#!/usr/bin/env python3
"""
Sphinx documentation build script
"""

import os
import shutil
import subprocess
import sys
from typing import Callable, NamedTuple, Tuple

cwd = os.getcwd()

# Sphinx commands
CMD_SPHINXBUILD = "sphinx-build"
CMD_SPHINX_AUTOGEN = "sphinx-autogen"

# File paths
DIR_MAKE_PY = os.path.dirname(os.path.realpath(__file__))
DIR_PACKAGE_SRC = os.path.join(cwd, os.pardir, "src")
DIR_SPHINX_SOURCE = os.path.join(cwd, "source")
DIR_SPHINX_AUX = os.path.join(cwd, "auxiliary")
DIR_SPHINX_API_GENERATED = os.path.join(DIR_SPHINX_SOURCE, "apidoc")
DIR_SPHINX_BUILD = os.path.join(cwd, "build")
DIR_SPHINX_TEMPLATES = os.path.join(DIR_MAKE_PY, "source", "_templates")
DIR_SPHINX_AUTOSUMMARY_TEMPLATE = os.path.join(DIR_SPHINX_TEMPLATES, "autosummary.rst")
DIR_SPHINX_TUTORIAL = os.path.join(DIR_SPHINX_SOURCE, "tutorial")
DIR_NOTEBOOKS = os.path.join(DIR_PACKAGE_SRC, os.pardir, "notebooks")

# Environment variables
# noinspection SpellCheckingInspection
ENV_PYTHON_PATH = "PYTHONPATH"


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
    if os.path.exists(DIR_SPHINX_BUILD):
        shutil.rmtree(path=DIR_SPHINX_BUILD)


def fun_apidoc() -> None:
    """
    Run Sphinx apidoc.
    """
    print_running_command(cmd=apidoc)

    packages = "\n   ".join(
        package for package in os.listdir(DIR_PACKAGE_SRC) if package[:1].isalnum()
    )

    autosummary_rst = f""".. autosummary::
   :toctree: ../apidoc
   :template: custom-module-template.rst
   :recursive:

   {packages}
"""

    with open(DIR_SPHINX_AUTOSUMMARY_TEMPLATE, "wt") as f:
        f.writelines(autosummary_rst)

    autogen_options = " ".join(
        [
            # template path
            "-t",
            quote_path(DIR_SPHINX_TEMPLATES),
            # include imports
            "-i",
            # the autosummary source file
            quote_path(DIR_SPHINX_AUTOSUMMARY_TEMPLATE),
        ]
    )

    if os.path.exists(DIR_SPHINX_API_GENERATED):
        shutil.rmtree(path=DIR_SPHINX_API_GENERATED)

    old_python_path = os.environ.get(ENV_PYTHON_PATH, None)
    try:
        os.environ[ENV_PYTHON_PATH] = DIR_PACKAGE_SRC

        subprocess.run(
            args=f"{CMD_SPHINX_AUTOGEN} {autogen_options}", shell=True, check=True
        )
    finally:
        if old_python_path is None:
            del os.environ[ENV_PYTHON_PATH]
        else:
            os.environ[ENV_PYTHON_PATH] = old_python_path


def fun_html() -> None:
    """
    Run a Sphinx build for generating HTML.
    """

    print_running_command(cmd=html)
    os.makedirs(DIR_SPHINX_BUILD, exist_ok=True)
    sphinx_html_opts = [
        "-M html",
        quote_path(DIR_SPHINX_SOURCE),
        quote_path(DIR_SPHINX_BUILD),
    ]
    subprocess.run(
        args=f"{CMD_SPHINXBUILD} {' '.join(sphinx_html_opts)}", shell=True, check=True
    )

    # create interactive versions of all notebooks

    sys.path.append(DIR_MAKE_PY)
    # noinspection PyUnresolvedReferences
    from source.scripts.transform_notebook import docs_notebooks_to_interactive

    for notebook_source_dir in [DIR_SPHINX_TUTORIAL, DIR_SPHINX_AUX]:
        if os.path.isdir(notebook_source_dir):
            docs_notebooks_to_interactive(notebook_source_dir, DIR_NOTEBOOKS)


# Define MakeCommands
clean = MakeCommand(
    command="clean",
    description="remove Sphinx build output",
    python_target=fun_clean,
    depends_on=(),
)
apidoc = MakeCommand(
    command="apidoc",
    description="generate Sphinx apidoc from sources.",
    python_target=fun_apidoc,
    depends_on=(),
)
html = MakeCommand(
    command="html",
    description="build Sphinx docs as HTML",
    python_target=fun_html,
    depends_on=(clean, apidoc),
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
    """
    Quote a file path if it contains whitespace.
    """
    if " " in path or "\t" in path:
        return f'"{path}"'
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
