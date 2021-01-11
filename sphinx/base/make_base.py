#!/usr/bin/env python3
"""
Sphinx documentation build script
"""
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from glob import glob
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, Set, Tuple, Type

from packaging import version as pkg_version

cwd = os.getcwd()

# Sphinx commands
CMD_SPHINX_BUILD = "sphinx-build"
CMD_SPHINX_AUTOGEN = "sphinx-autogen"

# File paths
DIR_MAKE_BASE = os.path.dirname(os.path.realpath(__file__))
DIR_REPO_ROOT = os.path.realpath(os.path.join(os.getcwd(), os.pardir))
DIR_REPO_PARENT = os.path.realpath(os.path.join(DIR_REPO_ROOT, os.pardir))
FACET_PROJECT = os.path.split(os.path.realpath(DIR_REPO_ROOT))[1]
DIR_PACKAGE_SRC = os.path.join(DIR_REPO_ROOT, "src")
DIR_DOCS = os.path.join(DIR_REPO_ROOT, "docs")
DIR_SPHINX_SOURCE = os.path.join(cwd, "source")
DIR_SPHINX_AUX = os.path.join(cwd, "auxiliary")
DIR_SPHINX_API_GENERATED = os.path.join(DIR_SPHINX_SOURCE, "apidoc")
DIR_SPHINX_GSTART_GENERATED = os.path.join(DIR_SPHINX_SOURCE, "getting_started")
DIR_SPHINX_BUILD = os.path.join(cwd, "build")
DIR_SPHINX_BUILD_HTML = os.path.join(DIR_SPHINX_BUILD, "html")
DIR_SPHINX_TEMPLATES = os.path.join(DIR_SPHINX_SOURCE, "_templates")
DIR_SPHINX_SOURCE_BASE = os.path.join(DIR_MAKE_BASE, os.pardir, "source")
DIR_SPHINX_TEMPLATES_BASE = os.path.join(DIR_SPHINX_SOURCE_BASE, "_templates")
DIR_SPHINX_AUTOSUMMARY_TEMPLATE = os.path.join(DIR_SPHINX_TEMPLATES, "autosummary.rst")
DIR_SPHINX_TUTORIAL = os.path.join(DIR_SPHINX_SOURCE, "tutorial")
DIR_SPHINX_SOURCE_STATIC_BASE = os.path.join(DIR_SPHINX_SOURCE_BASE, "_static_base")
JS_VERSIONS_FILE = os.path.join(DIR_SPHINX_SOURCE_STATIC_BASE, "js", "versions.js")
DIR_ALL_DOCS_VERSIONS = os.path.join(DIR_SPHINX_BUILD, "docs-version")

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
        if os.path.exists(DIR_SPHINX_API_GENERATED):
            shutil.rmtree(path=DIR_SPHINX_API_GENERATED)
        if os.path.exists(DIR_SPHINX_GSTART_GENERATED):
            shutil.rmtree(path=DIR_SPHINX_GSTART_GENERATED)


class ApiDoc(Command):
    @classmethod
    def get_description(cls) -> str:
        return "generate Sphinx API documentation from sources"

    @classmethod
    def get_dependencies(cls) -> Tuple[Type["Command"], ...]:
        # noinspection PyRedundantParentheses
        return (Clean,)

    @classmethod
    def _run(cls) -> None:
        packages = [
            package for package in os.listdir(DIR_PACKAGE_SRC) if package[:1].isalnum()
        ]
        print(f"Generating api documentation for {', '.join(packages)}")

        package_lines = "\n   ".join(packages)
        # noinspection SpellCheckingInspection
        autosummary_rst = f""".. autosummary::
   :toctree: ../apidoc
   :template: custom-module-template.rst
   :recursive:

   {package_lines}
"""

        os.makedirs(os.path.dirname(DIR_SPHINX_AUTOSUMMARY_TEMPLATE), exist_ok=True)
        with open(DIR_SPHINX_AUTOSUMMARY_TEMPLATE, "wt") as f:
            f.writelines(autosummary_rst)
        autogen_options = " ".join(
            [
                # template path
                "-t",
                quote_path(DIR_SPHINX_TEMPLATES_BASE),
                # include imports
                "-i",
                # the autosummary source file
                quote_path(DIR_SPHINX_AUTOSUMMARY_TEMPLATE),
            ]
        )

        subprocess.run(
            args=f"{CMD_SPHINX_AUTOGEN} {autogen_options}",
            shell=True,
            check=True,
        )


class GettingStartedDoc(Command):

    @classmethod
    def get_description(cls) -> str:
        return "generate getting started documentation from sources"

    @classmethod
    def get_dependencies(cls) -> Tuple[Type["Command"], ...]:
        # noinspection PyRedundantParentheses
        return (Clean,)

    @classmethod
    def _run(cls) -> None:

        # make dir if it does not exist
        os.makedirs(DIR_SPHINX_GSTART_GENERATED, exist_ok=True)

        # open the rst readme file
        with open(os.path.join(DIR_REPO_ROOT, "README.rst"), 'r') as file:
            readme_data = file.read()

        # modify links (step back needed as build will add sub directory to paths)
        readme_data = readme_data.replace('sphinx/source/', '../')
        readme_data = readme_data.replace('sphinx/auxiliary/', '../')
        readme_data = re.sub(
            r'\.\. Begin-Badges.*?\.\. End-Badges',
            '',
            readme_data,
            flags=re.S
        )

        # create a new getting_started.rst that combines the header from templates and
        # adds an include for the README
        with open(
            os.path.join(DIR_SPHINX_TEMPLATES_BASE, "getting-started-header.rst"),
            'r'
        ) as file:
            template_data = file.read()

        with open(os.path.join(DIR_SPHINX_GSTART_GENERATED,
                  "getting_started.rst"), "wt") as file:
            file.writelines(template_data)
            file.writelines(readme_data)


class FetchPkgVersions(Command):
    @classmethod
    def get_description(cls) -> str:
        return "fetch available package versions with docs"

    @classmethod
    def get_dependencies(cls) -> Tuple[Type["Command"], ...]:
        return ()

    @classmethod
    def _run(cls) -> None:
        os.makedirs(DIR_SPHINX_BUILD, exist_ok=True)
        start_from_version_tag = "1.0.1"
        sp = subprocess.run(
            args='git tag -l "*.*.*"', shell=True, check=True, stdout=subprocess.PIPE
        )
        version_tags = sp.stdout.decode("UTF-8").split("\n")
        version_tags = [
            vt for vt in version_tags if vt != "" and vt >= start_from_version_tag
        ]

        # add version currently build into version_tags
        version_built = get_package_version()

        if version_built not in version_tags:
            version_tags.append(version_built)

        version_tags.sort()
        version_tags.reverse()
        version_tags_non_rc = [vt for vt in version_tags if "rc" not in vt]
        latest_non_rc_version = version_tags_non_rc[0]

        print("Found the following version tags: ", version_tags)
        print("Latest non-RC version: ", latest_non_rc_version)

        version_data = {
            "current": latest_non_rc_version,
            "non_rc": version_tags_non_rc,
            "all": version_tags,
        }

        version_data_as_js = (
            f"const DOCS_VERSIONS = {json.dumps(version_data, indent=4,)}"
        )

        with open(JS_VERSIONS_FILE, "wt") as f:
            f.write(version_data_as_js)

        print(f"Version data written into: {JS_VERSIONS_FILE}")


class PrepareDocsDeployment(Command):
    @classmethod
    def get_description(cls) -> str:
        return "update versions of rendered documentation"

    @classmethod
    def get_dependencies(cls) -> Tuple[Type["Command"], ...]:
        return ()

    @classmethod
    def _run(cls) -> None:
        assert is_azure_build(), "Only implemented for Azure Pipelines"
        # get current version of package in the form of folder/URL name (e.g., "1-0-0")
        current_version = version_string_to_url(get_package_version())
        # remove docs build currently deployed, except for the docs versions folder
        if os.path.exists(os.path.join(DIR_DOCS, "docs-version")):
            with TemporaryDirectory() as DIR_TMP:
                shutil.move(src=os.path.join(DIR_DOCS, "docs-version"), dst=DIR_TMP)
                shutil.rmtree(path=DIR_DOCS)
                os.makedirs(DIR_DOCS)
                shutil.move(src=os.path.join(DIR_TMP, "docs-version"), dst=DIR_DOCS)

        # copy new docs version to deployment path
        os.makedirs(DIR_DOCS, exist_ok=True)
        shutil.copytree(src=DIR_SPHINX_BUILD_HTML, dst=DIR_DOCS, dirs_exist_ok=True)

        # update latest version in docs history
        if os.path.exists(os.path.join(DIR_DOCS, "docs-version", current_version)):
            shutil.rmtree(path=os.path.join(DIR_DOCS, "docs-version", current_version))
        shutil.copytree(
            src=DIR_ALL_DOCS_VERSIONS,
            dst=os.path.join(DIR_DOCS, "docs-version"),
            dirs_exist_ok=True,
        )

        # Replace all docs version lists with the most up-to-date to have all versions
        # accessible also from older versions
        new_versions_js = os.path.join(DIR_DOCS, "_static", "js", "versions.js")
        for d in glob(os.path.join(DIR_DOCS, "docs-version", "*", "")):
            old_versions_js = os.path.join(d, "_static", "js", "versions.js")
            shutil.copyfile(src=new_versions_js, dst=old_versions_js)

        # remove .buildinfo which interferes with GitHub Pages build
        if os.path.exists(os.path.join(DIR_DOCS, ".buildinfo")):
            os.remove(os.path.join(DIR_DOCS, ".buildinfo"))

        # create empty file to signal that no GitHub auto-rendering is required
        open(os.path.join(DIR_DOCS, ".nojekyll"), "a").close()

        print("Docs moved to ./docs and historic versions updated")


class Html(Command):
    @classmethod
    def get_description(cls) -> str:
        return "build Sphinx docs as HTML"

    @classmethod
    def get_dependencies(cls) -> Tuple[Type["Command"], ...]:
        return Clean, FetchPkgVersions, ApiDoc, GettingStartedDoc

    @classmethod
    def _run(cls) -> None:

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

        # create interactive versions of all notebooks
        sys.path.append(DIR_MAKE_BASE)

        # create copy of this build for the docs archive
        version_built = get_package_version()
        dir_path_this_build = os.path.join(
            DIR_ALL_DOCS_VERSIONS, version_string_to_url(version_built)
        )

        os.makedirs(DIR_ALL_DOCS_VERSIONS, exist_ok=True)
        if os.path.exists(dir_path_this_build):
            shutil.rmtree(dir_path_this_build)

        shutil.copytree(
            src=DIR_SPHINX_BUILD_HTML,
            dst=dir_path_this_build,
        )

        if not is_azure_build():
            shutil.move(src=DIR_ALL_DOCS_VERSIONS, dst=DIR_SPHINX_BUILD_HTML)

        # empty versions file to blank template
        with open(JS_VERSIONS_FILE, "wt") as f:
            f.write("")


class Help(Command):
    @classmethod
    def get_description(cls) -> str:
        return "print this help message"

    @classmethod
    def _run(cls) -> None:
        print_usage()


def make(*, modules: List[str]) -> None:
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

    # set up the Python path
    module_paths = [
        os.path.abspath(os.path.join(DIR_REPO_PARENT, module, "src"))
        for module in modules
    ]
    if ENV_PYTHON_PATH in os.environ:
        module_paths.append(os.environ[ENV_PYTHON_PATH])
    os.environ[ENV_PYTHON_PATH] = os.pathsep.join(module_paths)

    # run all given commands:
    executed_commands: Set[Type[Command]] = set()

    for next_command_name in commands_passed:

        next_command: Type[Command] = available_commands[next_command_name]

        for prerequisite_command in next_command.get_prerequisites():

            if prerequisite_command not in executed_commands:
                prerequisite_command.run()
                executed_commands.add(prerequisite_command)

        next_command.run()
        executed_commands.add(next_command)


def quote_path(path: str) -> str:
    """
    Quote a file path if it contains whitespace.
    """
    if " " in path or "\t" in path:
        return f'"{path}"'
    else:
        return path


def get_package_version() -> str:
    """
    Retrieve the package version for the project from __init__ or _version
    """
    project_src = os.path.abspath(os.path.join(DIR_REPO_ROOT, "src"))

    if FACET_PROJECT in ("sklearndf", "flow"):
        # for sklearndf and flow __init__ can't be trivially imported due to import
        # dependencies. Load the version as defined in FACET_PROJECT._version module
        spec = importlib.util.spec_from_file_location(
            "_version", os.path.join(project_src, FACET_PROJECT, "_version.py")
        )
    else:
        # pytools/facet: retrieve version from __init__.py
        spec = importlib.util.spec_from_file_location(
            "_version", os.path.join(project_src, FACET_PROJECT, "__init__.py")
        )

    version_module = importlib.util.module_from_spec(spec)
    # noinspection PyUnresolvedReferences
    spec.loader.exec_module(version_module)
    # noinspection PyUnresolvedReferences
    return version_module.__version__


def is_azure_build() -> bool:
    """
    Check if this is an Azure DevOps pipelines build
    """
    return "BUILD_REASON" in os.environ


def version_string_to_url(version: str) -> str:
    """
    Make a Python package version string safe for URLs/folders.

    Our convention is to only replace all dots with dashes.
    """
    return version.replace(".", "-")


def check_sphinx_version() -> None:
    import sphinx

    sphinx_version = pkg_version.parse(sphinx.__version__)
    if sphinx_version < pkg_version.parse("3.2.1"):
        raise RuntimeError("please upgrade sphinx to version 3.2.1 or newer")


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
    cmd.get_name(): cmd
    for cmd in (Clean, ApiDoc, GettingStartedDoc, Html, Help, FetchPkgVersions,
                PrepareDocsDeployment)
}
