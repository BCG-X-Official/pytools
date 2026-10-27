# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`pytools` (PyPI/conda dist name `gamma-pytools`) is BCG GAMMA's library of general ML and visualisation utilities: API development tools, expression building/rendering, fitting, joblib-based parallelisation, a lean MVC framework for visualisations (matplotlib / HTML / text), and more. It supports Python >=3.10 and is a dependency of other Facet projects. Source is in `src/pytools/`, tests in `test/test/pytools/`.

## Commands

Set up the dev environment (conda env `pytools-develop` + pre-commit hooks):

```sh
./dev-setup.sh        # conda env create -f environment.yml; pre-commit install
```

Tests (pytest config lives in `tox.ini`; `testpaths = test/test/`):

```sh
pytest                                              # all tests
pytest test/test/pytools/test_api.py                # one file
pytest test/test/pytools/test_api.py::test_name -s  # one test
```

Lint / format / type check (all run via pre-commit; hook versions are pinned in `.pre-commit-config.yaml`):

```sh
pre-commit run --all-files
black src test            # black is pinned via required-version in pyproject.toml; line length 88
isort src test            # profile=black, config in tox.ini
flake8 --config tox.ini src test
mypy --config-file pyproject.toml src/ test/ sphinx/   # strict mode
```

Build (wrapper around conda-build / tox that exports the `pyproject.toml` dependency matrices as `FACET_V_*` env vars):

```sh
./make.py pytools conda default      # build-system: conda|tox; dependencies: default|min|max
```

Docs: `sphinx/make.py` (delegates to `sphinx/base/make_base.py`).

`sphinx/base/` (`conf_base.py`, `make_base.py`, `_static`, `_templates`) is the shared docs build used by pytools, sklearndf and facet. pytools is the only source: `../sklearndf` and `../facet` download these files from GitHub at build time (their `sphinx/base/` is gitignored) from the pytools branch named by `BRANCH` in their `sphinx/make.py`, currently `2.1.x`, so a change here reaches them only once that branch is updated or points to `3.0.x`. Keep `conf_base.py` valid for all three, e.g. facet has a `sphinx/source/_static` folder and the others do not. The docs build fails on Sphinx configuration errors, such as `intersphinx_mapping` entries that share a target URI.

## Architecture

### Public/private module pattern and `AllTracker`

This is the central convention of the codebase. Each subpackage (`api`, `data`, `expression`, `viz`, ...) implements everything in private underscore-prefixed modules (e.g. `_alltracker.py`, `_matplot.py`). Each private module:

1. creates `__all__ = [...]` and a module-level `__tracker = AllTracker(globals())` near the top, before any public definitions;
2. ends with `__tracker.validate()` to verify that every public definition is listed in `__all__`.

The package's `__init__.py` then does `from ._x import *`. `pytools.api.AllTracker` (in `src/pytools/api/_alltracker.py`) enforces this: it rejects unlisted public definitions, exported global constants, and re-exported imports unless explicitly allowed via `allow_global_constants` / `allow_imported_definitions`. It also resolves forward type references in annotations via `update_forward_references` (using `typing.get_type_hints`), which is sensitive to Python version changes. When adding public symbols, follow this pattern, or imports will fail at module load.

### Subpackages

- `api` — decorators (`@subsdoc`, `@inheritdoc`, `@appenddoc`, ...), runtime validation helpers, `AllTracker`, and the docstring validator.
- `expression` — composable expression objects (atomic/composite/operator) with pluggable formatters (`formatter/`) and `repr/`.
- `viz` — MVC framework: drawers/styles render the same model as matplotlib, HTML, notebook or plain text; `viz/dendrogram` builds on it.
- `data` — linkage trees, matrices, simulated classification/regression data, taxonomy.
- `fit`, `parallelization`, `asyncio`, `http`, `meta`, `repr`, `text`, `typing`, `sphinx` — smaller utility modules; `sphinx` holds the Sphinx extensions/callbacks used for docs builds across Facet projects.

### Dependencies and build

Runtime dependency ranges are in `pyproject.toml` (`[tool.flit.metadata]`); `[build.matrix.min|max]` define the oldest/newest supported dependency sets used by `make.py` for CI matrix builds. Build backend is flit. `typing_inspect` is being phased out in favour of the `typing` stdlib (`get_origin`, `get_args`) as part of Python 3.14 support.

### CI and releasing

`azure-pipelines.yml` runs on pushes to `3.0.x` and `release/*`, on PRs targeting either, and nightly on `3.0.x`; a push to a `dev/*` branch alone does not trigger it. The full build matrix (min/default/max dependencies on Python 3.10/3.13/3.14, conda and tox) runs for PRs from `dev/*` or `release/*` branches and for the nightly build, so config problems can first show up on a `dev/*` PR. Other PRs run only a three-job essential subset, and only if build config files (`pyproject.toml`, `tox.ini`, `make.py`, ...) changed. The build tool versions installed by the tox jobs (`tox`, `flit`) must work on the newest Python in the matrix. Whenever the `flit` command line is installed with pip, also pin `flit_core>=2,<4` (as in `[build-system]` of `pyproject.toml`): `flit` itself does not limit `flit_core`, and flit_core 4 rejects the `[tool.flit.metadata]` table, so `flit install` and `flit publish` fail.

Publishing (anaconda.org, PyPI, GitHub release, docs to github-pages) happens only for builds of a `release/*` branch, i.e. after the `dev/<version>` PR is merged, never during the PR build itself. The only branch prefixes the pipeline recognises are `dev/` and `release/`; the `develop` branch is legacy.

Release process (full description in `sphinx/source/contribution_guide.rst`; releases 3.0.0 to 3.0.2 followed it):

1. Bump `__version__` in `src/pytools/__init__.py` and add the release notes to `RELEASE_NOTES.rst` on the baseline branch (`3.0.x`).
2. Create `dev/<version>` from the baseline branch, and `release/<version>` from the **tag of the previous release** (e.g. `release/3.0.3` from tag `3.0.2`). The pipeline checks that the package version matches the `dev/` or `release/` branch suffix; a pipeline run on the freshly created `release/<version>` fails this check until the dev PR is merged.
3. Open a PR `dev/<version>` -> `release/<version>` (not into the baseline branch) and wait for the full pipeline. Optionally test-upload the pip package to TestPyPI first, since PyPI versions are immutable.
4. Merge the PR with a **merge commit**, never a squash. This triggers the release stage: tag, GitHub release with artifacts, and upload to anaconda.org (`bcgx`) and PyPI. This is irreversible; always confirm before merging.
5. Merge `release/<version>` back into the baseline branch, then bump the version there towards the next release.

`3.0.x` is a protected branch: merging requires an approval (or admin override).

## Conventions

- Docstrings use Sphinx/reST (`:param x:`, `:return:`), and cross-reference via `:class:`/`:func:` roles; the API docs are generated from them.
- Release notes are in `RELEASE_NOTES.rst`.
- `.claude/` contains a project workflow (commands/skills for spec -> plan -> implement, Jira, PRs) and a coding-standards pack under `.claude/context/coding-standards/`; consult it via the `coding-standards` skill when asked to follow house standards.
