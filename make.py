#!/usr/bin/env python3
"""
Facet build script wrapping conda-build, and exposing matrix
dependency definition of pyproject.toml as environment variables
"""
import importlib
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import warnings
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

if FACET_PATH_ENV in os.environ and os.environ[FACET_PATH_ENV] != "":
    FACET_PATH = os.environ[FACET_PATH_ENV]
else:
    FACET_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))

if " " in FACET_PATH:
    warnings.warn(
        f"The build base path '{FACET_PATH}' contains spaces – this causes issues "
        f"with conda-build. Consider to set a different path using the "
        f"environment variable {FACET_PATH_ENV} ahead of running make.py"
    )

KNOWN_COMMANDS = "build"

KNOWN_PROJECTS = ("pytools", "sklearndf", "facet", "flow")

B_CONDA = "conda"
B_TOX = "tox"
KNOWN_BUILD_SYSTEMS = (B_CONDA, B_TOX)

DEFAULT_DEPS = "default"
MIN_DEPS = "min"
MAX_DEPS = "max"
UNCONSTRAINED_DEPS = "unconstrained"
KNOWN_DEPENDENCY_TYPES = (DEFAULT_DEPS, MIN_DEPS, MAX_DEPS, UNCONSTRAINED_DEPS)

CONDA_BUILD_PATH_SUFFIX = os.path.join("dist", "conda")
TOX_BUILD_PATH_SUFFIX = os.path.join("dist", "tox")


def make_build_path(project: str, build_system: str) -> str:
    """
    Return the target build path for Conda or Tox build.
    """
    if build_system == B_CONDA:
        return os.path.abspath(
            os.path.join(os.environ[FACET_PATH_ENV], project, CONDA_BUILD_PATH_SUFFIX)
        )
    elif build_system == B_TOX:
        return os.path.abspath(
            os.path.join(os.environ[FACET_PATH_ENV], project, TOX_BUILD_PATH_SUFFIX)
        )


def make_local_pypi_index_path(project: str) -> str:
    """
    Return the path where the local PyPi index for
    the given project should be placed.
    """
    return os.path.join(make_build_path(project, B_TOX), "simple")


def get_pyproject_toml(project: str) -> Dict[str, Any]:
    """
    Retrieve a parsed Dict for a given project's pyproject.toml.
    """
    pyproject_toml_path = os.path.join(FACET_PATH, project, "pyproject.toml")
    with open(pyproject_toml_path, "rt") as f:
        return toml.load(f)


def get_package_dist_name(project: str) -> str:
    """
    Retrieves from pyproject.toml for a project the appropriate
    dist-name. E.g. "gamma-pytools" for project "pytools".
    """
    return get_pyproject_toml(project)["tool"]["flit"]["metadata"]["dist-name"]


def get_package_version(project: str) -> str:
    """
    Retrieve the package version for the project from __init__ or _version
    """
    project_src = os.path.abspath(
        os.path.join(os.environ[FACET_PATH_ENV], project, "src")
    )

    if project in ("sklearndf", "flow"):
        # for sklearndf and flow __init__ can't be trivially imported due to import
        # dependencies. Load the version as defined in project._version module
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
    return version_module.__version__


def expose_deps(project: str, build_system: str, dependency_type: str) -> None:
    """
    Expose package dependencies for builds as environment variables.
    """
    pyproject_toml = get_pyproject_toml(project)

    def adapt_version_syntax(version: str) -> str:
        if build_system == B_CONDA or (">" in version or "<" in version):
            return version
        else:
            # PIP expects == instead of =
            return version.replace("=", "==")

    dependencies_to_expose = {}

    flit_metadata = pyproject_toml["tool"]["flit"]["metadata"]

    pkg_requires_python_version = flit_metadata["requires-python"]

    dependencies_to_expose["python"] = pkg_requires_python_version

    default_deps_definition: List[str] = flit_metadata["requires"]

    for default_dep in default_deps_definition:
        dependency_name, dependency_version = default_dep.strip().split(" ", maxsplit=1)
        dependencies_to_expose[dependency_name] = dependency_version

    if dependency_type != DEFAULT_DEPS:
        build_matrix_definition = pyproject_toml["build"]["matrix"]
        dependencies = build_matrix_definition[dependency_type]
        for (dependency_name, dependency_version) in dependencies.items():
            dependencies_to_expose[dependency_name] = adapt_version_syntax(
                dependency_version
            )

    for d_name, d_version in dependencies_to_expose.items():
        # bash ENV variables can not use dash, replace it to _
        env_var_key = f"FACET_V_{d_name.replace('-','_')}".upper().strip()
        env_var_value = d_version.strip()
        print(f"Exposing: '{env_var_key}' as: '{env_var_value}'")
        os.environ[env_var_key] = env_var_value


def clean(project: str, build_system: str) -> None:
    """
    Cleans the dist folder for the given project and build system.
    """
    build_path = make_build_path(project, build_system)
    if build_system == B_CONDA:
        # purge pre-existing build directories
        package_dist_name = get_package_dist_name(project)
        for obsolete_folder in glob(os.path.join(build_path, f"{package_dist_name}_*")):
            print(f"Clean: Removing obsolete conda-build folder at: {obsolete_folder}")
            shutil.rmtree(obsolete_folder, ignore_errors=True)

        # remove broken packages
        shutil.rmtree(os.path.join(build_path, "broken"), ignore_errors=True)

    elif build_system == B_TOX:
        # nothing to do – .tar.gz of same version will simply be replaced and
        # .tox is useful to keep
        pass


def set_up(project: str, build_system: str, dependency_type: str) -> None:
    """
    Set up for a build – set FACET_PATH (parent folder of all projects) and clean.
    """
    os.environ[FACET_PATH_ENV] = FACET_PATH
    os.environ[FACET_PATH_URI_ENV] = f"file://{pathname2url(FACET_PATH)}"
    clean(project, build_system)
    expose_deps(project, build_system, dependency_type)
    pkg_version = get_package_version(project)
    os.environ[
        FACET_BUILD_PKG_VERSION_ENV.format(project=project.upper())
    ] = pkg_version
    print("==============================================")
    print(
        f"STARTING {build_system.upper()} BUILD FOR: {project},"
        f" VERSION: {pkg_version}"
    )
    print("==============================================")


def conda_build(project: str, dependency_type: str) -> None:
    """
    Build a facet project using conda-build.
    """
    set_up(project, build_system=B_CONDA, dependency_type=dependency_type)

    def _mk_conda_channel_arg(_project) -> str:
        return f'-c "{pathlib.Path(make_build_path(_project, B_CONDA)).as_uri()}"'

    build_path = make_build_path(project, B_CONDA)
    os.environ[CONDA_BUILD_PATH_ENV] = build_path

    recipe_path = os.path.abspath(
        os.path.join(os.environ[FACET_PATH_ENV], project, "condabuild")
    )

    local_channels = [
        _mk_conda_channel_arg(p)
        for p in KNOWN_PROJECTS
        if os.path.exists(make_build_path(p, B_CONDA))
        and os.path.exists(
            os.path.join(make_build_path(p, B_CONDA), "noarch/repodata.json")
        )
    ]

    print(f"Building: {project}. Build path: {build_path}")
    os.makedirs(build_path, exist_ok=True)
    build_cmd = f"conda-build -c conda-forge {' '.join(local_channels)} {recipe_path}"
    print(f"Build Command: {build_cmd}")
    subprocess.run(args=build_cmd, shell=True, check=True)


def tox_build(project: str, dependency_type: str) -> None:
    """
    Build a facet project using tox.
    """
    set_up(project, B_TOX, dependency_type)
    if dependency_type == DEFAULT_DEPS:
        tox_env = "py3"
    else:
        tox_env = "py3-custom-deps"

    build_cmd = f"tox -e {tox_env} -v"
    print(f"Build Command: {build_cmd}")
    subprocess.run(args=build_cmd, shell=True, check=True)
    print("Tox build completed – creating local PyPi index")
    create_local_pypi_index(project)


def create_local_pypi_index(project: str) -> None:
    """
    Creates/updates a local PyPI PEP 503 (the simple repository API) compliant
    folder structure, so that it can be used with PIP's --extra-index-url
    setting.
    """
    main_tox_build_path = make_build_path(project, B_TOX)
    pypi_index_path = make_local_pypi_index_path(project)
    project_dist_name = get_package_dist_name(project)
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
        f"<a href='{os.path.basename(package)}'>{os.path.basename(package)}</a><br />"
        for package in glob(os.path.join(project_repo_path, package_glob))
    ]
    # store index.html
    with open(project_index_html_path, "wt") as f:
        f.writelines(package_file_links)

    print(f"Local PyPi Index created at: {pypi_index_path}")


def print_usage() -> None:
    """
    Print a help string to explain the usage of this script.
    """
    usage = """Facet Build script
=================================
Available program arguments:
    <project> <build-system> <dependencies>
        create the Conda package for given project.

    Available arguments:
        project:    i.e. pytools | sklearndf | facet | flow.
                    Use "build=all" to build pytools, sklearndf, facet and flow.

        build-system: conda | tox

        dependencies:
            default: use dependencies and version ranges as defined in pyproject.toml
            min:     use a custom set of minimal dependencies from pyproject.toml
            max:     use a custom set of maximum dependencies from pyproject.toml
            unconstrained: use constrained dependencies from pyproject.toml


Example usage:
    ./make.py sklearndf conda default
    ./make.py sklearndf tox unconstrained

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
            print(f"Wrong {arg_name}: {arg_passed}. Allowed are: {known_args}")
            exit(1)

    if project == ALL_PROJECTS_QUALIFIER:
        for _project in KNOWN_PROJECTS:
            if build_system == B_CONDA:
                conda_build(_project, dependency_type)
            elif build_system == B_TOX:
                tox_build(_project, dependency_type)
    else:
        if build_system == B_CONDA:
            conda_build(project, dependency_type)
        elif build_system == B_TOX:
            tox_build(project, dependency_type)


if __name__ == "__main__":
    run_make()
