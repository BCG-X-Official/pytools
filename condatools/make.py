#!/usr/bin/env python3
"""
Facet build script wrapping conda-build
"""

import os
import pathlib
import shutil
import subprocess
import sys

ALL_PROJECTS_QUALIFIER = "all"

CWD = os.getcwd()
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
KNOWN_PROJECTS = ("pytools", "sklearndf", "facet")
FACET_PATH_ENV = "FACET_PATH"
CONDA_BLD_PATH_ENV = "CONDA_BLD_PATH"
BLD_PATH_SUFFIX = "dist/conda"


def make_build_path(project: str) -> str:
    """
    Return the target build path for Conda-build.
    """
    return os.path.abspath(
        os.path.join(os.environ[FACET_PATH_ENV], project, BLD_PATH_SUFFIX)
    )


def set_up(project) -> None:
    """
    Set up for a build – set FACET_PATH (parent folder of all projects) and clean.
    """
    facet_path = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir))
    os.environ[FACET_PATH_ENV] = facet_path
    shutil.rmtree(make_build_path(project), ignore_errors=True)


def build(project: str) -> None:
    """
    Build a facet project using conda-build.
    """
    set_up(project)

    def _mk_conda_channel_arg(_project):
        return f"""-c "{pathlib.Path(make_build_path(_project)).as_uri()}" """

    build_path = make_build_path(project)
    os.environ[CONDA_BLD_PATH_ENV] = build_path

    recipe_path = os.path.abspath(
        os.path.join(os.environ[FACET_PATH_ENV], project, "conda-build")
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


def print_usage() -> None:
    """
    Print a help string to explain the usage of this script.
    """
    usage = """Facet Conda build script
=================================
Available program arguments:
    <project>   create the Conda package for given project.
                Use "all" to build pytools, sklearndf and facet.

Example usage:
    ./make.py sklearndf

"""
    print(usage)


def run_make() -> None:
    """
    Run this build script with the given arguments.
    """
    if len(sys.argv) < 2:
        print_usage()
        exit(1)

    project = sys.argv[1].strip().lower()

    if project not in KNOWN_PROJECTS and project != ALL_PROJECTS_QUALIFIER:
        print(f"Wrong project argument: {project}. Allowed are: {KNOWN_PROJECTS}")
        exit(1)
    elif project == ALL_PROJECTS_QUALIFIER:
        for _project in KNOWN_PROJECTS:
            build(_project)
    else:
        build(project=project)

    print(f"Conda-build completed for {project}.")


if __name__ == "__main__":
    run_make()
