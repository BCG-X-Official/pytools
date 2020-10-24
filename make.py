#!/usr/bin/env python3
"""
Facet build script wrapping conda-build, and exposing matrix
dependency definition of pyproject.toml as environment variables
"""
import importlib
import os
import pathlib
import shutil
import subprocess
import sys
from typing import List

import toml

ALL_PROJECTS_QUALIFIER = "all"

CWD = os.getcwd()
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
FACET_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
KNOWN_COMMANDS = "build"

KNOWN_PROJECTS = ("pytools", "sklearndf", "facet")

B_CONDA = "conda"
B_TOX = "tox"
KNOWN_BUILD_SYSTEMS = (B_CONDA, B_TOX)

DEFAULT_DEPS = "default"
MIN_DEPS = "min"
MAX_DEPS = "max"
UNCONSTRAINED_DEPS = "unconstrained"
KNOWN_DEPENDENCY_TYPES = (DEFAULT_DEPS, MIN_DEPS, MAX_DEPS, UNCONSTRAINED_DEPS)

FACET_PATH_ENV = "FACET_PATH"
FACET_BUILD_PKG_VERSION_ENV = "FACET_BUILD_{project}_VERSION"
CONDA_BUILD_PATH_ENV = "CONDA_BLD_PATH"
BUILD_PATH_SUFFIX = os.path.join("dist", "conda")


def make_build_path(project: str) -> str:
    """
    Return the target build path for Conda-build.
    """
    return os.path.abspath(
        os.path.join(os.environ[FACET_PATH_ENV], project, BUILD_PATH_SUFFIX)
    )


def get_package_version(project: str) -> str:
    """
    Retrieve the package version for the project from __init__ or _version
    """
    project_src = os.path.abspath(
        os.path.join(os.environ[FACET_PATH_ENV], project, "src")
    )

    if project == "sklearndf":
        # for sklearndf __init__ can't be trivially imported due to import dependencies
        # Load the version as defined in sklearndf._version module
        spec = importlib.util.spec_from_file_location(
            "_version", os.path.join(project_src, "sklearndf", "_version.py")
        )
    else:
        # pytools/facet: retrieve version from __init__.py
        spec = importlib.util.spec_from_file_location(
            "_version", os.path.join(project_src, project, "__init__.py")
        )

    version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version_module)
    return version_module.__version__


def expose_deps(project: str, build_system: str, dependency_type: str) -> None:
    """
    Expose package dependencies for builds as environment variables.
    """
    pyproject_toml_path = os.path.join(FACET_PATH, project, "pyproject.toml")
    with open(pyproject_toml_path, "rt") as f:
        pyproject_toml = toml.load(f)

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
        env_var_key = f"FACET_V_{d_name}".upper().strip()
        env_var_value = d_version.strip()
        print(f"Exposing: '{env_var_key}' as: '{env_var_value}'")
        os.environ[env_var_key] = env_var_value


def set_up(project: str, build_system: str, dependency_type: str) -> None:
    """
    Set up for a build – set FACET_PATH (parent folder of all projects) and clean.
    """
    os.environ[FACET_PATH_ENV] = FACET_PATH
    shutil.rmtree(make_build_path(project), ignore_errors=True)
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

    def _mk_conda_channel_arg(_project):
        return f"""-c "{pathlib.Path(make_build_path(_project)).as_uri()}" """

    build_path = make_build_path(project)
    os.environ[CONDA_BUILD_PATH_ENV] = build_path

    recipe_path = os.path.abspath(
        os.path.join(os.environ[FACET_PATH_ENV], project, "condabuild")
    )

    local_channels = [
        _mk_conda_channel_arg(p)
        for p in KNOWN_PROJECTS
        if os.path.exists(make_build_path(p))
        and os.path.exists(os.path.join(make_build_path(p), "noarch/repodata.json"))
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
        project:    i.e. pytools | sklearndf | facet.
                    Use "build=all" to build pytools, sklearndf and facet.

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
