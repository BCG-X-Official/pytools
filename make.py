#!/usr/bin/env python3
"""
Facet build script wrapping conda-build, and exposing matrix
dependency definition of pyproject.toml as environment variables
"""
import importlib
import importlib.util
import itertools
import os
import re
import shutil
import subprocess
import sys
import warnings
from abc import ABCMeta, abstractmethod
from glob import glob
from typing import Any, Dict, Iterator, List, Set, cast
from urllib import request
from xml.etree import ElementTree

import toml
from packaging.version import Version

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

B_CONDA = "conda"
B_TOX = "tox"
KNOWN_BUILD_SYSTEMS = {B_CONDA, B_TOX}

DEP_DEFAULT = "default"
DEP_MIN = "min"
DEP_MAX = "max"
KNOWN_DEPENDENCY_TYPES = {DEP_DEFAULT, DEP_MIN, DEP_MAX}

CONDA_BUILD_PATH_SUFFIX = os.path.join("dist", "conda")
TOX_BUILD_PATH_SUFFIX = os.path.join("dist", "tox")

PKG_PYTHON = "python"

RE_VERSION = re.compile(
    r"(?:\s*"
    r"(?:[<>]=?|[!~=]=)\s*"
    r"\d+(?:\.\d+)*"
    r"(?:\.?(?:a|b|rc|dev)\d*|\.\*)?\s*,?"
    r")+(?<!,)"
)


class Builder(metaclass=ABCMeta):
    def __init__(self, project: str, dependency_type: str) -> None:
        self.project = project
        self.dependency_type = dependency_type

        if dependency_type not in KNOWN_DEPENDENCY_TYPES:
            raise ValueError(
                f"arg dependency_type must be one of {KNOWN_DEPENDENCY_TYPES}"
            )

        # determine the projects root path containing the project working directories

        self.projects_root_path = projects_root_path = get_projects_root_path()

        # add the project roots path to the environment as a URI

        os.environ[
            FACET_PATH_URI_ENV
        ] = f"file://{request.pathname2url(projects_root_path)}"

        # determine the package version of the project

        project_root_path = os.path.abspath(os.path.join(projects_root_path, project))
        src_root_path = os.path.join(project_root_path, "src", project)
        version_path = os.path.join(src_root_path, "_version.py")

        if os.path.exists(version_path):
            # For some projects, __init__ can't be trivially imported due to import
            # dependencies.
            # Therefore we first try to get the version from a project._version module.
            spec = importlib.util.spec_from_file_location("_version", version_path)
        else:
            # otherwise: retrieve the version from __init__.py
            spec = importlib.util.spec_from_file_location(
                "_version", os.path.join(src_root_path, "__init__.py")
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
            raise ValueError(f"Unknown build system: {build_system}")

    @property
    @abstractmethod
    def build_system(self) -> str:
        pass

    @property
    @abstractmethod
    def build_path_suffix(self) -> str:
        pass

    def make_build_path(self) -> str:
        """
        Return the target build path for Conda or Tox build.
        """

        return os.path.abspath(
            os.path.join(
                os.environ[FACET_PATH_ENV], self.project, self.build_path_suffix
            )
        )

    def make_local_pypi_index_path(self) -> str:
        """
        Return the path where the local PyPi index for
        the given project should be placed.
        """
        return os.path.join(self.make_build_path(), "simple")

    def get_pyproject_toml(self) -> Dict[str, Any]:
        """
        Retrieve a parsed Dict for a given project's pyproject.toml.
        """
        pyproject_toml_path = os.path.join(
            os.environ[FACET_PATH_ENV], self.project, "pyproject.toml"
        )
        print(f"Reading build configuration from {pyproject_toml_path}")
        with open(pyproject_toml_path, "rt") as f:
            return toml.load(f)

    def get_package_dist_name(self) -> str:
        """
        Retrieves from pyproject.toml for a project the appropriate
        dist-name. E.g. "gamma-pytools" for project "pytools".
        """
        return self.get_pyproject_toml()[TOML_TOOL][TOML_FLIT][TOML_METADATA][
            TOML_DIST_NAME
        ]

    def validate_release_version(self) -> None:
        """
        Validate that the given version id can be used for the next release
        of the given package.
        """
        package: str = self.get_package_dist_name()
        new_version: Version = Version(self.package_version)

        print(f"Testing package version: {package} {new_version}")

        releases_uri = f"https://pypi.org/rss/project/{package}/releases.xml"

        print(f"Getting existing releases from {releases_uri}")
        with request.urlopen(releases_uri) as response:
            assert response.getcode() == 200, "Error getting releases from PyPi"
            releases_xml = response.read()

        tree = ElementTree.fromstring(releases_xml)
        releases_nodes = tree.findall(path=".//channel//item//title")

        released_versions: List[Version] = sorted(
            Version(r) for r in [r.text for r in releases_nodes]
        )

        print(f"Releases found on PyPi: {', '.join(map(str, released_versions))}")

        if new_version in released_versions:
            raise AssertionError(
                f"{package} {new_version} has already been released on PyPi"
            )

        if new_version.micro == 0 and not new_version.is_prerelease:
            # we have a major or minor release: need a release candidate
            pre_releases = [
                released_version
                for released_version in released_versions
                if (
                    released_version.is_prerelease
                    and released_version.release == new_version.release
                )
            ]

            if not pre_releases:
                raise AssertionError(
                    f"Release of major or minor version {new_version} "
                    f"requires at least one release candidate, e.g., "
                    f"{new_version.release[0]}.{new_version.release[1]}.rc0"
                )

            print(
                f"Pre-releases {pre_releases} exist; "
                f"release of major/minor version {new_version} can go ahead"
            )

    @abstractmethod
    def adapt_version_requirement_syntax(self, version: str) -> str:
        pass

    def expose_package_dependencies(self) -> None:
        """
        Export package dependencies for builds as environment variables.
        """

        # get full project specification from the TOML file
        pyproject_toml = self.get_pyproject_toml()

        # get the python version and run dependencies from the flit metadata
        flit_metadata = pyproject_toml[TOML_TOOL][TOML_FLIT][TOML_METADATA]

        python_version = flit_metadata[TOML_REQUIRES_PYTHON]
        run_dependencies: Dict[str, str] = {
            name: validate_pip_version_spec(
                dependency_type=DEP_DEFAULT, package=name, spec=version.lstrip()
            )
            for name, version in (
                (*package_spec.strip().split(" ", maxsplit=1), "")[:2]
                for package_spec in flit_metadata[TOML_REQUIRES]
            )
        }

        if PKG_PYTHON in run_dependencies:
            raise ValueError(
                f"do not include '{PKG_PYTHON}' in flit 'requires' property; "
                "use dedicated 'requires-python' property instead"
            )
        run_dependencies[PKG_PYTHON] = python_version

        # get the matrix test dependencies (min and max)
        build_matrix_definition = pyproject_toml[TOML_BUILD][TOML_MATRIX]

        def get_matrix_dependencies(matrix_type: str) -> Dict[str, str]:
            return {
                name: self.adapt_version_requirement_syntax(
                    validate_pip_version_spec(
                        dependency_type=matrix_type, package=name, spec=version
                    )
                )
                for name, version in build_matrix_definition[matrix_type].items()
            }

        min_dependencies: Dict[str, str] = get_matrix_dependencies(DEP_MIN)
        max_dependencies: Dict[str, str] = get_matrix_dependencies(DEP_MAX)

        # check that the matrix dependencies cover all run dependencies

        dependencies_not_covered_in_matrix: Set[str] = (
            run_dependencies.keys() - min_dependencies.keys()
        ) | (run_dependencies.keys() - max_dependencies.keys())

        if dependencies_not_covered_in_matrix:
            raise ValueError(
                "one or more run dependencies are not covered "
                "by the min and max matrix dependencies: "
                + ", ".join(dependencies_not_covered_in_matrix)
            )

        # expose requirements as environment variables

        if self.dependency_type == DEP_DEFAULT:
            requirements_to_expose = run_dependencies
        elif self.dependency_type == DEP_MIN:
            requirements_to_expose = min_dependencies
        else:
            assert self.dependency_type == DEP_MAX
            requirements_to_expose = max_dependencies

        # add packages that are only mentioned in the matrix requirements
        requirements_to_expose.update(
            {
                package: ""
                for package in itertools.chain(min_dependencies, max_dependencies)
                if package not in requirements_to_expose
            }
        )

        for package, version in requirements_to_expose.items():
            # bash ENV variables can not use dash, replace it to _
            env_var_name = "FACET_V_" + re.sub(r"[^\w]", "_", package.upper())
            print(f"Exporting {env_var_name}={version !r}")
            os.environ[env_var_name] = version

    @abstractmethod
    def clean(self) -> None:
        """
        Cleans the dist folder for the given project and build system.
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

    def run(self) -> None:
        self.print_build_info(stage="STARTING")
        self.validate_release_version()
        self.clean()
        self.expose_package_dependencies()
        self.build()
        self.print_build_info(stage="COMPLETED")


def validate_pip_version_spec(dependency_type: str, package: str, spec: str) -> str:
    if re.fullmatch(RE_VERSION, spec):
        return spec
    else:
        raise ValueError(
            f"invalid version spec in {dependency_type} dependency {package}{spec}"
        )


class CondaBuilder(Builder):
    def __init__(self, project: str, dependency_type: str):
        super().__init__(project, dependency_type)

        if " " in self.projects_root_path:
            warnings.warn(
                f"The build base path '{self.projects_root_path}' contains spaces – "
                f"this causes issues with conda-build. "
                f"Consider to set a different path using the "
                f"environment variable {FACET_PATH_ENV} ahead of running make.py."
            )

    @property
    def build_system(self) -> str:
        return B_CONDA

    @property
    def build_path_suffix(self) -> str:
        return CONDA_BUILD_PATH_SUFFIX

    def adapt_version_requirement_syntax(self, version: str) -> str:
        # CONDA expects = instead of ==
        return re.sub(r"==", "=", version)

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
        Build a facet project using conda-build.
        """

        build_path = self.make_build_path()
        os.environ[CONDA_BUILD_PATH_ENV] = build_path

        recipe_path = os.path.abspath(
            os.path.join(os.environ[FACET_PATH_ENV], self.project, "condabuild")
        )

        os.makedirs(build_path, exist_ok=True)
        build_cmd = f"conda-build -c conda-forge -c bcg_gamma {recipe_path}"
        print(
            f"Building: {self.project}\n"
            f"Build path: {build_path}\n"
            f"Build Command: {build_cmd}"
        )
        subprocess.run(args=build_cmd, shell=True, check=True)


class ToxBuilder(Builder):
    @property
    def build_system(self) -> str:
        return B_TOX

    @property
    def build_path_suffix(self) -> str:
        return TOX_BUILD_PATH_SUFFIX

    def adapt_version_requirement_syntax(self, version: str) -> str:
        return version

    def clean(self) -> None:
        # nothing to do – .tar.gz of same version will simply be replaced and
        # .tox is useful to keep
        pass

    def build(self) -> None:
        """
        Build a facet project using tox.
        """
        if self.dependency_type == DEP_DEFAULT:
            tox_env = "py3"
        else:
            tox_env = "py3-custom-deps"

        original_dir = os.getcwd()

        try:

            build_path = self.make_build_path()
            os.makedirs(build_path, exist_ok=True)
            os.chdir(build_path)

            build_cmd = f"tox -e {tox_env} -v"
            print(f"Build Command: {build_cmd}")
            subprocess.run(args=build_cmd, shell=True, check=True)
            print("Tox build completed – creating local PyPi index")

            # Create/update a local PyPI PEP 503 (the simple repository API) compliant
            # folder structure, so that it can be used with PIP's --extra-index-url
            # setting.

            pypi_index_path = self.make_local_pypi_index_path()
            project_dist_name = self.get_package_dist_name()
            project_repo_path = os.path.join(pypi_index_path, project_dist_name)
            project_index_html_path = os.path.join(project_repo_path, "index.html")
            os.makedirs(project_repo_path, exist_ok=True)

            package_glob = f"{project_dist_name}-*.tar.gz"

            # copy all relevant packages into the index subfolder
            for package in glob(package_glob):
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

        finally:
            os.chdir(original_dir)


def get_projects_root_path() -> str:
    if (FACET_PATH_ENV in os.environ) and os.environ[FACET_PATH_ENV]:
        facet_path = os.environ[FACET_PATH_ENV]
    else:
        facet_path = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
        os.environ[FACET_PATH_ENV] = facet_path

    return facet_path


def get_known_projects() -> Set[str]:
    dir_entries: Iterator[os.DirEntry] = cast(
        Iterator[os.DirEntry], os.scandir(get_projects_root_path())
    )
    return {dir_entry.name for dir_entry in dir_entries if dir_entry.is_dir()}


def print_usage() -> None:
    """
    Print a help string to explain the usage of this script.
    """
    print(
        f"""Facet Build script
==================
Build a distribution package for given project.

Available arguments:
    project:    {' | '.join(get_known_projects())}

    build-system: {B_CONDA} | {B_TOX}

    dependencies:
        default: use dependencies and version ranges as defined in pyproject.toml
        min:     use a custom set of minimal dependencies from pyproject.toml
        max:     use a custom set of maximum dependencies from pyproject.toml


Example usage:
    ./make.py sklearndf conda default
    ./make.py sklearndf tox max

"""
    )


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
        dependency_type = DEP_DEFAULT

    # sanitize input
    for arg_name, arg_value, valid_values in (
        ("project", project, get_known_projects()),
        ("build system", build_system, KNOWN_BUILD_SYSTEMS),
        ("dependency type", dependency_type, KNOWN_DEPENDENCY_TYPES),
    ):

        if arg_value not in valid_values:
            print(
                f"Wrong value for {arg_name} argument: "
                f"got {arg_value} but expected one of {', '.join(valid_values)}"
            )
            exit(1)

    Builder.for_build_system(
        build_system=build_system, project=project, dependency_type=dependency_type
    ).run()


if __name__ == "__main__":
    run_make()
