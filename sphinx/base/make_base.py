#!/usr/bin/env python3
"""
Sphinx documentation build script
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from glob import glob
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from weakref import ReferenceType

from make_util import get_package_version as _get_package_version
from packaging import version as pkg_version

DIR_SPHINX_ROOT = os.path.dirname(os.path.dirname(__file__))
assert (
    os.path.basename(DIR_SPHINX_ROOT) == "sphinx"
), f"Sphinx root dir {DIR_SPHINX_ROOT!r} is named 'sphinx'"

# Sphinx commands
CMD_SPHINX_BUILD = "sphinx-build"
CMD_SPHINX_AUTOGEN = "sphinx-autogen"

# File paths
DIR_SPHINX_BASE = os.path.dirname(os.path.realpath(__file__))
DIR_REPO_ROOT = os.path.dirname(DIR_SPHINX_ROOT)
DIR_REPO_PARENT = os.path.dirname(DIR_REPO_ROOT)
PROJECT_NAME = os.path.split(os.path.realpath(DIR_REPO_ROOT))[1]
DIR_PACKAGE_SRC = os.path.join(DIR_REPO_ROOT, "src")
DIR_DOCS = os.path.join(DIR_REPO_ROOT, "docs")
DIR_DOCS_VERSION = os.path.join(DIR_DOCS, "docs-version")
DIR_SPHINX_SOURCE = os.path.join(DIR_SPHINX_ROOT, "source")
DIR_SPHINX_AUX = os.path.join(DIR_SPHINX_ROOT, "auxiliary")
DIR_SPHINX_API_GENERATED = os.path.join(DIR_SPHINX_SOURCE, "apidoc")
DIR_SPHINX_GENERATED = os.path.join(DIR_SPHINX_SOURCE, "_generated")
DIR_SPHINX_BUILD = os.path.join(DIR_SPHINX_ROOT, "build")
DIR_SPHINX_BUILD_DOCS_VERSION = os.path.join(DIR_SPHINX_BUILD, "docs-version")
DIR_SPHINX_BUILD_HTML = os.path.join(DIR_SPHINX_BUILD, "html")
DIR_SPHINX_TEMPLATES = os.path.join(DIR_SPHINX_ROOT, "base", "_templates")
DIR_SPHINX_TUTORIAL = os.path.join(DIR_SPHINX_SOURCE, "tutorial")
DIR_PACKAGE_ROOT = os.path.abspath(os.path.join(DIR_REPO_ROOT, "src", PROJECT_NAME))

FILE_AUTOSUMMARY_TEMPLATE = os.path.join(DIR_SPHINX_GENERATED, "autosummary.rst_")
FILE_JS_VERSIONS_RELATIVE = os.path.join("_static", "js", "versions.js")
FILE_JS_VERSIONS = os.path.join(DIR_SPHINX_BASE, FILE_JS_VERSIONS_RELATIVE)

# Environment variables
# noinspection SpellCheckingInspection
ENV_PYTHON_PATH = "PYTHONPATH"


# Version of the package being built
PACKAGE_VERSION = _get_package_version(package_path=DIR_PACKAGE_ROOT)


class CommandMeta(ABCMeta):
    """
    Metaclass for command classes.

    Subsequent instantiations of a command class return the identical object.
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        cls.__instance_ref: Optional[ReferenceType[Command]] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> Command:
        """
        Return the existing command instance, or create a new one if none exists yet.

        :return: the command instance
        """
        if args or kwargs:
            raise ValueError("command classes may not take any arguments")

        if cls.__instance_ref:
            obj = cls.__instance_ref()
            if obj is not None:
                return obj

        instance: Command = super(CommandMeta, cls).__call__()
        cls.__instance_ref = ReferenceType(instance)
        return instance


class Command(metaclass=CommandMeta):
    """Defines an available command that can be launched from this module."""

    __RE_CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")

    def __init__(self) -> None:
        self.name = self.__RE_CAMEL_TO_SNAKE.sub("_", type(self).__name__).lower()

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    def get_dependencies(self) -> Tuple["Command", ...]:
        pass

    def get_prerequisites(self) -> Iterable["Command"]:
        dependencies_extended: List[Command] = []

        for dependency in self.get_dependencies():
            dependencies_inherited = dependency.get_dependencies()
            if self in dependencies_inherited:
                raise ValueError(
                    f"circular dependency: {dependency.name} depends on {self.name}"
                )
            dependencies_extended.extend(
                dependency
                for dependency in dependencies_inherited
                if dependency not in dependencies_extended
            )
            dependencies_extended.append(dependency)

        return dependencies_extended

    def run(self) -> None:
        command_message = f"Running command {self.name} – {self.get_description()}"
        separator = "=" * len(command_message)
        log("\n".join(["", separator, command_message, separator]))
        self._run()

    @abstractmethod
    def _run(self) -> None:
        pass


#
# commands
#


class Clean(Command):
    def get_description(self) -> str:
        return "remove Sphinx build output"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        if os.path.exists(DIR_SPHINX_BUILD):
            shutil.rmtree(path=DIR_SPHINX_BUILD)
        if os.path.exists(DIR_SPHINX_API_GENERATED):
            shutil.rmtree(path=DIR_SPHINX_API_GENERATED)
        if os.path.exists(DIR_SPHINX_GENERATED):
            shutil.rmtree(path=DIR_SPHINX_GENERATED)


class ApiDoc(Command):
    def get_description(self) -> str:
        return "generate Sphinx API documentation from sources"

    def get_dependencies(self) -> Tuple[Command, ...]:
        # noinspection PyRedundantParentheses
        return (Clean(),)

    def _run(self) -> None:
        packages = [
            package for package in os.listdir(DIR_PACKAGE_SRC) if package[:1].isalnum()
        ]
        log(f"Generating api documentation for {', '.join(packages)}")

        package_lines = "\n   ".join(packages)
        # noinspection SpellCheckingInspection
        autosummary_rst = f""".. autosummary::
   :toctree: ../apidoc
   :template: custom-module-template.rst
   :recursive:

   {package_lines}
"""

        os.makedirs(os.path.dirname(FILE_AUTOSUMMARY_TEMPLATE), exist_ok=True)
        with open(FILE_AUTOSUMMARY_TEMPLATE, "wt") as f:
            f.writelines(autosummary_rst)
        autogen_options = " ".join(
            [
                # template path
                "-t",
                quote_path(DIR_SPHINX_TEMPLATES),
                # include imports
                "-i",
                # the autosummary source file
                quote_path(FILE_AUTOSUMMARY_TEMPLATE),
            ]
        )

        subprocess.run(
            args=f"{CMD_SPHINX_AUTOGEN} {autogen_options}",
            shell=True,
            check=True,
        )


class GettingStartedDoc(Command):
    def get_description(self) -> str:
        return "generate getting started documentation from sources"

    def get_dependencies(self) -> Tuple[Command, ...]:
        # noinspection PyRedundantParentheses
        return (Clean(),)

    def _run(self) -> None:

        # make dir if it does not exist
        os.makedirs(DIR_SPHINX_GENERATED, exist_ok=True)

        # open the rst readme file
        with open(os.path.join(DIR_REPO_ROOT, "README.rst"), "r") as file:
            readme_data = file.read()

        # modify links (step back needed as build will add subdirectory to paths)
        readme_data = readme_data.replace("sphinx/source/", "/")
        readme_data = re.sub(
            r"\.\. Begin-Badges.*?\.\. End-Badges", "", readme_data, flags=re.S
        )

        with open(os.path.join(DIR_SPHINX_GENERATED, "release_notes.rst"), "w") as dst:
            dst.write(".. _release-notes:\n\n")
            with open(os.path.join(DIR_REPO_ROOT, "RELEASE_NOTES.rst"), "r") as src:
                dst.write(src.read())

        # create a new getting_started.rst that combines the header from templates and
        # adds an include for the README
        with open(
            os.path.join(DIR_SPHINX_TEMPLATES, "getting-started-header.rst"), "r"
        ) as file:
            template_data = file.read()

        with open(
            os.path.join(DIR_SPHINX_GENERATED, "getting_started.rst"),
            "wt",
        ) as file:
            file.writelines(template_data)
            file.writelines(readme_data)


class FetchPkgVersions(Command):
    def get_description(self) -> str:
        return "fetch available package versions with docs"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        versions = get_versions()

        version_data = {
            "current": str(versions.latest_version),
            "all": list(map(str, versions.version_tags)),
        }

        version_data_as_js = (
            f"const DOCS_VERSIONS = {json.dumps(version_data, indent=4,)}"
        )

        with open(FILE_JS_VERSIONS, "wt") as f:
            f.write(version_data_as_js)

        log(f"Version data written to: {FILE_JS_VERSIONS}")


class PrepareDocsDeployment(Command):
    def get_description(self) -> str:
        return "integrate documentation of previous versions"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        # we expect to find all previous documentation in docs/
        # and the newly built documentation in sphinx/build/
        if not is_azure_build():
            raise RuntimeError("only implemented for Azure Pipelines")

        # copy the new docs version to the deployment path
        self._copy_new_documentation()

        self._update_historic_docs()

        self._copy_latest_to_docs_root()

        self._tidy_up_docs_root()

    @staticmethod
    def _copy_new_documentation() -> None:
        log("Adding new documentation to documentation version history")

        os.makedirs(DIR_DOCS_VERSION, exist_ok=True)

        dir_docs_current_version = os.path.join(
            DIR_DOCS_VERSION,
            version_string_to_url(PACKAGE_VERSION),
        )

        if os.path.exists(dir_docs_current_version):
            # remove a previous version of the same documentation if it exists
            shutil.rmtree(dir_docs_current_version)

        # copy new docs version to deployment path
        shutil.copytree(src=DIR_SPHINX_BUILD_HTML, dst=dir_docs_current_version)

    @staticmethod
    def _update_historic_docs() -> None:
        # Replace all docs version lists with the most up-to-date to have all versions
        # accessible also from older versions
        new_versions_js = os.path.join(
            DIR_DOCS_VERSION,
            version_string_to_url(PACKAGE_VERSION),
            FILE_JS_VERSIONS_RELATIVE,
        )

        for d in glob(os.path.join(DIR_DOCS_VERSION, "*")):
            old_versions_js = os.path.join(d, FILE_JS_VERSIONS_RELATIVE)
            if old_versions_js != new_versions_js:
                log(
                    "Copying versions.js file from "
                    f"'{new_versions_js}' to '{old_versions_js}'"
                )
                shutil.copyfile(src=new_versions_js, dst=old_versions_js)

    @staticmethod
    def _copy_latest_to_docs_root() -> None:
        # copy the latest version to root

        dir_latest_version = os.path.join(
            DIR_DOCS_VERSION, version_string_to_url(get_versions().latest_version)
        )
        shutil.copytree(src=dir_latest_version, dst=DIR_DOCS, dirs_exist_ok=True)

    @staticmethod
    def _tidy_up_docs_root() -> None:
        # remove .buildinfo which interferes with GitHub Pages build
        file_build_info = os.path.join(DIR_DOCS, ".buildinfo")
        if os.path.exists(file_build_info):
            os.remove(file_build_info)

        # create empty file to signal that no GitHub auto-rendering is required
        # noinspection SpellCheckingInspection
        open(os.path.join(DIR_DOCS, ".nojekyll"), "a").close()


class Html(Command):
    def get_description(self) -> str:
        return "build Sphinx docs as HTML"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return Clean(), FetchPkgVersions(), ApiDoc(), GettingStartedDoc()

    def _run(self) -> None:

        check_sphinx_version()

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


class Help(Command):
    def get_description(self) -> str:
        return "print this help message"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        print_usage()


class Versions:
    """
    Helper class that lists all versions that have already been released.
    """

    def __init__(self, version_tags: Iterable[pkg_version.Version]) -> None:
        self.version_tags = sorted(version_tags, reverse=True)

    @property
    def latest_version(self) -> pkg_version:
        return self.version_tags[0]


_versions: Optional[Versions] = None


def get_versions() -> Versions:
    global _versions

    if _versions is not None:
        return _versions

    os.makedirs(DIR_SPHINX_BUILD, exist_ok=True)
    start_from_version_tag: pkg_version.Version = pkg_version.Version("1.0")

    version_tags: Iterable[pkg_version.Version] = (
        pkg_version.parse(s)
        for s in (
            subprocess.run(
                args='git tag -l "*.*.*"',
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
            )
            .stdout.decode("UTF-8")
            .split("\n")
        )
        if s
    )

    # append the version we are building to version_tags
    version_tags = (*version_tags, PACKAGE_VERSION)

    versions_by_minor_version: Dict[str, List[pkg_version.Version]] = defaultdict(list)

    for v in version_tags:
        if not (v.is_prerelease or v.is_devrelease) and v >= start_from_version_tag:
            versions_by_minor_version[f"{v.major}.{v.minor}"].append(v)

    minor_versions: List[pkg_version] = [
        max(versions) for versions in versions_by_minor_version.values()
    ]

    log(f"Found minor versions: {', '.join(map(str, minor_versions))}")

    _versions = Versions(minor_versions)
    return _versions


def make() -> None:
    """
    Run this make script with the given arguments.
    """
    if len(sys.argv) < 2:
        print_usage()

    commands_passed = sys.argv[1:]

    unknown_commands = set(commands_passed) - available_commands.keys()

    if unknown_commands:
        log(f"Unknown build commands: {' '.join(unknown_commands)}\n")
        print_usage()
        exit(1)

    # set up the Python path
    module_paths = [os.path.abspath(os.path.join(DIR_REPO_ROOT, "src"))]
    if ENV_PYTHON_PATH in os.environ:
        module_paths.append(os.environ[ENV_PYTHON_PATH])
    os.environ[ENV_PYTHON_PATH] = os.pathsep.join(module_paths)

    # run all given commands:
    executed_commands: Set[Command] = set()

    for next_command_name in commands_passed:

        next_command: Command = available_commands[next_command_name]

        for prerequisite_command in next_command.get_prerequisites():

            if prerequisite_command not in executed_commands:
                prerequisite_command.run()
                executed_commands.add(prerequisite_command)

        next_command.run()
        executed_commands.add(next_command)


def log(message: Any) -> None:
    """
    Write a message to `stderr`.

    :param message: the message to write
    """
    print(str(message), file=sys.stderr)


def quote_path(path: str) -> str:
    """
    Quote a file path if it contains whitespace.
    """
    if " " in path or "\t" in path:
        return f'"{path}"'
    else:
        return path


def is_azure_build() -> bool:
    """
    Check if this is an Azure DevOps pipelines build
    """
    is_azure = "BUILD_REASON" in os.environ

    if is_azure:
        log("Azure build detected")

    return is_azure


def version_string_to_url(version: pkg_version.Version) -> str:
    """
    Make a Python package version string safe for URLs/folders.

    Our convention is to only replace all dots with dashes.
    """
    return f"{version.major}-{version.minor}"


def check_sphinx_version() -> None:
    import sphinx

    sphinx_version = pkg_version.parse(sphinx.__version__)
    if sphinx_version < pkg_version.parse("4.5"):
        raise RuntimeError("please upgrade sphinx to version 4.5 or newer")


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


available_commands: Dict[str, Command] = {
    cmd.name: cmd
    for cmd in (
        Clean(),
        ApiDoc(),
        GettingStartedDoc(),
        Html(),
        Help(),
        FetchPkgVersions(),
        PrepareDocsDeployment(),
    )
}
