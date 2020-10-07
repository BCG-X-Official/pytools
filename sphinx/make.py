#!/usr/bin/env python3
"""
Sphinx documentation build script
"""

import os
import re
import shutil
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from typing import Dict, Iterable, List, Set, Tuple, Type

cwd = os.getcwd()

# Sphinx commands
CMD_SPHINX_BUILD = "sphinx-build"
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


class Command(metaclass=ABCMeta):
    """ Defines an available command that can be launched from this module."""

    __RE_CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")

    @classmethod
    def get_name(cls) -> str:
        try:
            return cls.__name
        except AttributeError:
            cls.__name = cls.__RE_CAMEL_TO_SNAKE.sub("_", cls.__name__).lower()
            return cls.__name

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        pass

    @classmethod
    def get_dependencies(cls) -> Tuple[Type["Command"], ...]:
        return ()

    @classmethod
    def get_prerequisites(cls) -> Iterable[Type["Command"]]:
        dependencies_extended: List[Type["Command"]] = []

        for dependency in cls.get_dependencies():
            dependencies_inherited = dependency.get_dependencies()
            if cls in dependencies_inherited:
                raise ValueError(
                    f"circular dependency: {dependency.get_name()} "
                    f"depends on {cls.get_name()}"
                )
            dependencies_extended.extend(
                dependency
                for dependency in dependencies_inherited
                if dependency not in dependencies_extended
            )
            dependencies_extended.append(dependency)

        return dependencies_extended

    @classmethod
    def run(cls) -> None:
        print(f"Running command {cls.get_name()} – {cls.get_description()}")
        cls._run()

    @classmethod
    @abstractmethod
    def _run(cls) -> None:
        pass


#
# commands
#


class Clean(Command):
    @classmethod
    def get_description(cls) -> str:
        return "remove Sphinx build output"

    @classmethod
    def _run(cls) -> None:
        if os.path.exists(DIR_SPHINX_BUILD):
            shutil.rmtree(path=DIR_SPHINX_BUILD)


class ApiDoc(Command):
    @classmethod
    def get_description(cls) -> str:
        return "generate Sphinx API documentation from sources"

    @classmethod
    def _run(cls) -> None:
        packages = "\n   ".join(
            package for package in os.listdir(DIR_PACKAGE_SRC) if package[:1].isalnum()
        )
        # noinspection SpellCheckingInspection
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


class Html(Command):
    @classmethod
    def get_description(cls) -> str:
        return "build Sphinx docs as HTML"

    @classmethod
    def get_dependencies(cls) -> Tuple[Type["Command"], ...]:
        return Clean, ApiDoc

    @classmethod
    def _run(cls) -> None:
        os.makedirs(DIR_SPHINX_BUILD, exist_ok=True)

        sphinx_html_opts = [
            "-M html",
            quote_path(DIR_SPHINX_SOURCE),
            quote_path(DIR_SPHINX_BUILD),
        ]

        subprocess.run(
            args=f"{CMD_SPHINX_BUILD} {' '.join(sphinx_html_opts)}",
            shell=True,
            check=True,
        )

        # create interactive versions of all notebooks
        sys.path.append(DIR_MAKE_PY)

        # noinspection PyUnresolvedReferences
        from source.scripts.transform_notebook import docs_notebooks_to_interactive

        for notebook_source_dir in [DIR_SPHINX_TUTORIAL, DIR_SPHINX_AUX]:
            if os.path.isdir(notebook_source_dir):
                docs_notebooks_to_interactive(notebook_source_dir, DIR_NOTEBOOKS)


class Help(Command):
    @classmethod
    def get_description(cls) -> str:
        return "print this help message"

    @classmethod
    def _run(cls) -> None:
        print_usage()


def make() -> None:
    """
    Run this make script with the given arguments.
    """
    if len(sys.argv) < 2:
        print_usage()

    commands_passed = sys.argv[1:]

    unknown_commands = set(commands_passed) - available_commands.keys()

    if unknown_commands:
        print(f"Unknown build commands: {' '.join(unknown_commands)}\n")
        print_usage()
        exit(1)

    # run all given commands:
    executed_commands: Set[Type[Command]] = set()
    for selected_cmd in commands_passed:
        known_cmd: Type[Command] = available_commands[selected_cmd]
        for prerequisite in known_cmd.get_prerequisites():
            if prerequisite not in executed_commands:
                prerequisite.run()

        known_cmd.run()
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
    usage = """Sphinx documentation build script
=================================

Available program arguments:
"""
    usage += "\n".join(
        f"\t{name} – {command.get_description()}"
        for name, command in available_commands.items()
    )
    print(usage)


available_commands: Dict[str, Type[Command]] = {
    cmd.get_name(): cmd for cmd in (Clean, ApiDoc, Html, Help)
}

if __name__ == "__main__":
    make()
