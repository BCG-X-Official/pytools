Release Notes
=============

*pytools* 1.1
-------------

1.1.2
~~~~~

- Catch up with fixes and pipeline updates introduced by pytools 1.0.3 and 1.0.4
- API: support inheriting class docstrings from superclasses using the
  :func:`.inheritdoc` decorator
- API: new :func:`.subsdoc` decorator to replace text in docstrings
- API: use background color for matrix grid in :class:`.MatrixMatplotStyle`


1.1.1
~~~~~

- API: :class:`.MatplotStyle` now uses PyPlot's current axes by default, instead of
  creating a new figure and axis


1.1.0
~~~~~

- API: :class:`.JobRunner` provides a new object-oriented interface to :mod:`joblib`,
  running instances of :class:`.Job` and :class:`.JobQueue` in parallel
- API: :class:`.AllTracker` detects and prohibits exporting objects imported from other
  modules
- API: :class:`.AllTracker` detects and prohibits exporting global constants (the
  preferred approach is to define constants inside classes as this provides better
  context, and will be properly documented via Sphinx)


*pytools* 1.0
-------------

1.0.5
~~~~~

- FIX: back-port 1.1 bugfix for building multi-version documentation


1.0.4
~~~~~

- FIX: do not substitute `~=` by `~==` when adapting version syntax for tox


1.0.3
~~~~~

This is a maintenance release focusing on enhancements to the CI/CD pipeline, along with
minor fixes.

- BUILD: add the `bcg_gamma` conda channel when building
- BUILD: Enforce pre-release for minor and major releases
- DOC: add pre-commit hook instructions to contribution guide
- BUILD: update flake8 to v3.9.0
- BUILD: apply make_base.py changes from 1.1.x also on develop (adds more robust parsing
  of package versions)
- FIX: version syntax adaptation with mixed `=` and `>=`


1.0.2
~~~~~

This is a maintenance release focusing on enhancements to the CI/CD pipeline, along with
minor fixes.

- API: sort list of items returned by :meth:`.AllTracker.get_tracked`
- API: add protected method to class :class:`.MatplotStyle` to apply color scheme to
  :class:`~matplotlib.axes.Axes` object
- FIX: preserve correct instance for subclasses of singleton classes
- FIX: add a few missing type hints
- BUILD: add support for numpy 1.20
- BUILD: updates and changes to the CI/CD pipeline


1.0.1
~~~~~

Initial release.
