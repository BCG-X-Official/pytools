#!/usr/bin/env python3
"""
Facet build script wrapping conda-build, and exposing matrix
dependency definition of pyproject.toml as environment variables
"""
import importlib
import importlib.util
import os
import pathlib
import re
import shutil
import subprocess
import sys
import warnings
from abc import ABCMeta, abstractmethod
from glob import glob
from typing import Any, Dict, List
from urllib.request import pathname2url

import toml

ALL_PROJECTS_QUALIFIER = "all"

CWD = os.getcwd()
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

FACET_PATH_ENV = "FACET_PATH"
FACET_PATH_URI_ENV = "FACET_PATH_URI"
FACET_BUILD_PKG_VERSION_ENV = "FACET_BUILD_{project}_VERSION"
CONDA_BUILD_PATH_ENV = "CONDA_BLD_PATH"

# pyproject.toml: elements of the hierarchy
TOML_BUILD = "build"
TOML_DIST_NAME = "dist-name"
TOML_FLIT = "flit"
TOML_MATRIX = "matrix"
TOML_METADATA = "metadata"
TOML_REQUIRES = "requires"
TOML_REQUIRES_PYTHON = "requires-python"
TOML_TOOL = "tool"


PROJ_PYTOOLS = "pytools"
PROJ_FACET = "facet"
PROJ_FLOW = "flow"
PROJ_SKLEARNDF = "sklearndf"
KNOWN_PROJECTS = {PROJ_PYTOOLS, PROJ_SKLEARNDF, PROJ_FACET, PROJ_FLOW}

B_CONDA = "conda"
B_TOX = "tox"
KNOWN_BUILD_SYSTEMS = {B_CONDA, B_TOX}

DEFAULT_DEPS = "default"
MIN_DEPS = "min"
MAX_DEPS = "max"
KNOWN_DEPENDENCY_TYPES = {DEFAULT_DEPS, MIN_DEPS, MAX_DEPS}

CONDA_BUILD_PATH_SUFFIX = os.path.join("dist", "conda")
TOX_BUILD_PATH_SUFFIX = os.path.join("dist", "tox")


class Builder(metaclass=ABCMeta):
    def __init__(self, project: str, dependency_type: str):
        self.project = project
        self.dependency_type = dependency_type

        # determine the FACET root path containing the project working directories

        if (FACET_PATH_ENV in os.environ) and os.environ[FACET_PATH_ENV]:
            facet_path = os.environ[FACET_PATH_ENV]
        else:
            facet_path = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
            os.environ[FACET_PATH_ENV] = facet_path

        if " " in facet_path:
            warnings.warn(
                f"The build base path '{facet_path}' contains spaces – "
                f"this causes issues with conda-build. "
                f"Consider to set a different path using the "
                f"environment variable {FACET_PATH_ENV} ahead of running make.py."
            )
        os.environ[FACET_PATH_URI_ENV] = f"file://{pathname2url(facet_path)}"

        # determine the package version of the project

        project_src = os.path.abspath(os.path.join(facet_path, project, "src"))
        if project in (PROJ_SKLEARNDF, PROJ_FLOW):
            # For sklearndf and flow,
            # __init__ can't be trivially imported due to import dependencies.
            # Load the version as defined in project._version module.
            spec = importlib.util.spec_from_file_location(
                "_version", os.path.join(project_src, project, "_version.py")
            )
        else:
            # pytools/facet: retrieve version from __init__.py
            spec = importlib.util.spec_from_file_location(
                "_version", os.path.join(project_src, project, "__init__.py")
            )
        version_module = importlib.util.module_from_spec(spec)
        # noinspection PyUnresolvedReferences
        spec.loader.exec_module(version_module)
        # noinspection PyUnresolvedReferences
        package_version = version_module.__version__

        os.environ[
            FACET_BUILD_PKG_VERSION_ENV.format(project=project.upper())
        ] = package_version

        self.package_version = package_version

    @staticmethod
    def for_build_system(
        build_system: str, project: str, dependency_type: str
    ) -> "Builder":
        if build_system == B_CONDA:
            return CondaBuilder(project=project, dependency_type=dependency_type)
        elif build_system == B_TOX:
            return ToxBuilder(project=project, dependency_type=dependency_type)
        else:
            raise KeyError(f"Unknown build system: {build_system}")

    @property
    @abstractmethod
    def build_system(self) -> str:
        pass

    @property
    @abstractmethod
    def build_path_suffix(self) -> str:
        pass

    def make_build_path(self, project: str = None) -> str:
        """
        Return the target build path for Conda or Tox build.
        """

        if project is None:
            project = self.project

        return os.path.abspath(
            os.path.join(os.environ[FACET_PATH_ENV], project, self.build_path_suffix)
        )

    def make_local_pypi_index_path(self) -> str:
        """
        Return the path where the local PyPi index for
        the given self.project should be placed.
        """
        return os.path.join(self.make_build_path(), "simple")

    def get_pyproject_toml(self) -> Dict[str, Any]:
        """
        Retrieve a parsed Dict for a given self.project's pyproject.toml.
        """
        pyproject_toml_path = os.path.join(
            os.environ[FACET_PATH_ENV], self.project, "pyproject.toml"
        )
        print(f"Reading build configuration from {pyproject_toml_path}")
        with open(pyproject_toml_path, "rt") as f:
            return toml.load(f)

    def get_package_dist_name(self) -> str:
        """
        Retrieves from pyproject.toml for a self.project the appropriate
        dist-name. E.g. "gamma-pytools" for self.project "pytools".
        """
        return self.get_pyproject_toml()[TOML_TOOL][TOML_FLIT][TOML_METADATA][
            TOML_DIST_NAME
        ]

    @abstractmethod
    def adapt_version_syntax(self, version: str) -> str:
        pass

    def expose_deps(self) -> None:
        """
        Expose package dependencies for builds as environment variables.
        """
        pyproject_toml = self.get_pyproject_toml()

        dependencies_to_expose = {}

        flit_metadata = pyproject_toml[TOML_TOOL][TOML_FLIT][TOML_METADATA]

        pkg_requires_python_version = flit_metadata[TOML_REQUIRES_PYTHON]

        dependencies_to_expose["python"] = pkg_requires_python_version

        default_deps_definition: List[str] = flit_metadata[TOML_REQUIRES]

        for default_dep in default_deps_definition:
            dependency_name: str
            dependency_version: str
            dependency_name, dependency_version = default_dep.strip().split(
                " ", maxsplit=1
            )
            dependencies_to_expose[dependency_name] = dependency_version.strip()

        if self.dependency_type != DEFAULT_DEPS:
            build_matrix_definition = pyproject_toml[TOML_BUILD][TOML_MATRIX]
            dependencies = build_matrix_definition[self.dependency_type]
            for (dependency_name, dependency_version) in dependencies.items():
                dependencies_to_expose[dependency_name] = self.adapt_version_syntax(
                    dependency_version
                )

        for d_name, d_version in dependencies_to_expose.items():
            # bash ENV variables can not use dash, replace it to _
            env_var_key = f"FACET_V_{d_name.replace('-','_')}".upper().strip()
            env_var_value = d_version.strip()
            print(f"Exposing: '{env_var_key}' as: '{env_var_value}'")
            os.environ[env_var_key] = env_var_value

    @abstractmethod
    def clean(self) -> None:
        """
        Cleans the dist folder for the given self.project and build system.
        """

    def print_build_info(self, stage: str) -> None:
        message = (
            f"{stage} {self.build_system.upper()} BUILD FOR {self.project}, "
            f"VERSION {self.package_version}"
        )
        separator = "=" * len(message)
        print(f"{separator}\n{message}\n{separator}")

    @abstractmethod
    def build(self) -> None:
        pass

    def create_local_pypi_index(self) -> None:
        """
        Creates/updates a local PyPI PEP 503 (the simple repository API) compliant
        folder structure, so that it can be used with PIP's --extra-index-url
        setting.
        """
        main_tox_build_path = self.make_build_path()
        pypi_index_path = self.make_local_pypi_index_path()
        project_dist_name = self.get_package_dist_name()
        project_repo_path = os.path.join(pypi_index_path, project_dist_name)
        project_index_html_path = os.path.join(project_repo_path, "index.html")
        os.makedirs(project_repo_path, exist_ok=True)

        package_glob = f"{project_dist_name}-*.tar.gz"

        # copy all relevant packages into the index subfolder
        for package in glob(os.path.join(main_tox_build_path, package_glob)):
            shutil.copy(package, project_repo_path)

        # remove index.html, if exists already
        if os.path.exists(project_index_html_path):
            os.remove(project_index_html_path)

        # create an index.html with entries for all existing packages
        package_file_links = [
            f"<a href='{os.path.basename(package)}'>{os.path.basename(package)}</a>"
            f"<br/>"
            for package in glob(os.path.join(project_repo_path, package_glob))
        ]
        # store index.html
        with open(project_index_html_path, "wt") as f:
            f.writelines(package_file_links)

        print(f"Local PyPi Index created at: {pypi_index_path}")

    def run(self) -> None:
        self.print_build_info(stage="STARTING")
        self.clean()
        self.expose_deps()
        self.build()
        self.print_build_info(stage="COMPLETED")


class CondaBuilder(Builder):
    @property
    def build_system(self) -> str:
        return B_CONDA

    @property
    def build_path_suffix(self) -> str:
        return CONDA_BUILD_PATH_SUFFIX

    def adapt_version_syntax(self, version: str) -> str:
        return version

    def clean(self) -> None:
        build_path = self.make_build_path()
        # purge pre-existing build directories
        package_dist_name = self.get_package_dist_name()
        for obsolete_folder in glob(os.path.join(build_path, f"{package_dist_name}_*")):
            print(f"Clean: Removing obsolete conda-build folder at: {obsolete_folder}")
            shutil.rmtree(obsolete_folder, ignore_errors=True)

        # remove broken packages
        shutil.rmtree(os.path.join(build_path, "broken"), ignore_errors=True)

    def build(self) -> None:
        """
        Build a facet self.project using conda-build.
        """

        build_path = self.make_build_path()
        os.environ[CONDA_BUILD_PATH_ENV] = build_path

        recipe_path = os.path.abspath(
            os.path.join(os.environ[FACET_PATH_ENV], self.project, "condabuild")
        )

        local_channels = [
            f'-c "{pathlib.Path(_build_path).as_uri()}"'
            for _build_path in map(self.make_build_path, KNOWN_PROJECTS)
            if os.path.exists(_build_path)
            and os.path.exists(os.path.join(_build_path, "noarch/repodata.json"))
        ]

        print(f"Building: {self.project}. Build path: {build_path}")
        os.makedirs(build_path, exist_ok=True)
        build_cmd = (
            f"conda-build -c conda-forge "
            f"-c bcg_gamma {' '.join(local_channels)} {recipe_path}"
        )
        print(f"Build Command: {build_cmd}")
        subprocess.run(args=build_cmd, shell=True, check=True)


class ToxBuilder(Builder):
    @property
    def build_system(self) -> str:
        return B_TOX

    @property
    def build_path_suffix(self) -> str:
        return TOX_BUILD_PATH_SUFFIX

    def adapt_version_syntax(self, version: str) -> str:
        # PIP expects == instead of =
        return re.sub(r"(?<![<=>~])=(?![<=>])", "==", version)

    def clean(self) -> None:
        # nothing to do – .tar.gz of same version will simply be replaced and
        # .tox is useful to keep
        pass

    def build(self) -> None:
        """
        Build a facet self.project using tox.
        """
        if self.dependency_type == DEFAULT_DEPS:
            tox_env = "py3"
        else:
            tox_env = "py3-custom-deps"

        build_cmd = f"tox -e {tox_env} -v"
        print(f"Build Command: {build_cmd}")
        subprocess.run(args=build_cmd, shell=True, check=True)
        print("Tox build completed – creating local PyPi index")
        self.create_local_pypi_index()


def print_usage() -> None:
    """
    Print a help string to explain the usage of this script.
    """
    usage = f"""Facet Build script
==================
Build a distribution package for given project.

Available arguments:
    project:    {' | '.join((ALL_PROJECTS_QUALIFIER,*KNOWN_PROJECTS))}
                use "{ALL_PROJECTS_QUALIFIER}" to build all projects

    build-system: {B_CONDA} | {B_TOX}

    dependencies:
        default: use dependencies and version ranges as defined in pyproject.toml
        min:     use a custom set of minimal dependencies from pyproject.toml
        max:     use a custom set of maximum dependencies from pyproject.toml


Example usage:
    ./make.py sklearndf conda default
    ./make.py sklearndf tox max

"""
    print(usage)


def run_make() -> None:
    """
    Run this build script with the given arguments.
    """
    if len(sys.argv) < 3:
        print_usage()
        exit(1)

    project = sys.argv[1]
    build_system = sys.argv[2]

    if len(sys.argv) > 3:
        dependency_type = sys.argv[3]
    else:
        dependency_type = DEFAULT_DEPS

    # sanitize input
    for arg_name, arg_passed, known_args in (
        ("project", project, KNOWN_PROJECTS),
        ("build system", build_system, KNOWN_BUILD_SYSTEMS),
        ("dependency type", dependency_type, KNOWN_DEPENDENCY_TYPES),
    ):

        if arg_name == "project" and arg_passed == "all":
            continue
        elif arg_passed not in known_args:
            print(
                f"Wrong {arg_name}: {arg_passed}; fallowed are: {', '.join(known_args)}"
            )
            exit(1)

    if project == ALL_PROJECTS_QUALIFIER:
        for _project in KNOWN_PROJECTS:
            Builder.for_build_system(
                build_system=build_system,
                project=_project,
                dependency_type=dependency_type,
            ).run()
    else:
        Builder.for_build_system(
            build_system=build_system, project=project, dependency_type=dependency_type
        ).run()


if __name__ == "__main__":
    run_make()
