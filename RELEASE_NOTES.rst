Release Notes
=============

*pytools* 1.2
-------------

1.2.5
~~~~~

This is a maintenance release to catch up with *pytools* 1.1.10.


1.2.4
~~~~~

This is a maintenance release to catch up with *pytools* 1.1.8.


1.2.3
~~~~~

This release enhances support for generating Sphinx documentation, and catches up with
*pytools* 1.1.7.

- API: add sphinx processor :class:`.ResolveGenericClassParameters`
  to substitute generic type parameters introduced by base classes or via the
  ``self`` and ``cls`` special method arguments
- API: add sphinx processor :class:`.AutodocProcessBases` to handle
  `autodoc-process-bases` events (introduced in Sphinx 4.1)
- API: function :func:`.validate_type` now accepts multiple alternative types to
  validate values against, in line with how :func:`isinstance` tests for multiple types


1.2.2
~~~~~

This is a maintenance release to catch up with *pytools* 1.1.5.


1.2.1
~~~~~

This is a maintenance release to catch up with *pytools* 1.1.4.


1.2.0
~~~~~

- API: new function :func:`.to_collection` preserves any type of collection, and
  converts iterators into :class:`tuple` instances
- API: functions :func:`.to_set`, :func:`.to_list`, :func:`.to_tuple`,
  :func:`.to_collection`, and :func:`.validate_element_types` now accept multiple
  alternative types to validate elements against, in line with how :func:`isinstance`
  tests for multiple types
- BUILD: add support for :mod:`matplotlib` ~= 3.0, :mod:`scipy` ~= 1.6,
  and `typing-inspect <https://github.com/ilevkivskyi/typing_inspect>`__ ~= 0.7


*pytools* 1.1
-------------

1.1.10
~~~~~~

This release addresses additional issues in the release process, focusing on the
`make_base.py` script for Sphinx builds used across *gamma-pytools*, *sklearndf*, and
*gamma-facet*.


1.1.9
~~~~~

This is a bugfix release to restore the GitHub release process.


1.1.8
~~~~~

- BUILD: the ``make_base.py`` build script no longer imports the actual module to obtain
  the current package version, similarly as introduced for ``make.py`` in
  *pytools* 1.1.7


1.1.7
~~~~~

- BUILD: update the ``make.py`` build script to remove its reliance on importing the
  actual module just to obtain the build version; instead, ``make.py`` now scans the
  top-level ``__init__.py`` file for a ``__version__`` declaration


1.1.6
~~~~~

- VIZ: set colors of axis labels to the foreground color of the current color scheme
- FIX: ensure correct weight labels when rendering dendrograms as plain text using the
  :class:`.DendrogramReportStyle`
- FIX: calling method :meth:`.Id.get_class_id` could cause a :class:`.TypeError`
- FIX: :class:`.Replace3rdPartyDoc` sphinx callback now substitutes 3rd-party docstrings
  also for :class:`.property` definitions


1.1.5
~~~~~

- FIX: fixed a rare case where :meth:`.Expression.eq_` returned ``False`` for two
  equivalent expressions if one of them included an :class:`.ExpressionAlias`
- FIX: accept any type of numerical values as leaf weights of :class:`.LinkageTree`


1.1.4
~~~~~

- BUILD: add support for :mod:`joblib` 1.0.*


1.1.3
~~~~~

- FIX: comparing two :class:`.InfixExpression` objects using method
  :meth:`.Expression.eq_` would erroneously yield ``True`` if both expressions
  had the same operator but a different number of operands, and the operands of the
  shorter expression were equal to the operands at the start of the longer expression


1.1.2
~~~~~

- Catch up with fixes and pipeline updates introduced by *pytools* 1.0.3 and 1.0.4
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

1.0.6
~~~~~

- FIX: back-port 1.1 bugfix for :meth:`.Expression.eq_`


1.0.5
~~~~~

- FIX: back-port 1.1 bugfix for building multi-version documentation


1.0.4
~~~~~

- FIX: do not substitute ``~=`` by ``~==`` when adapting version syntax for tox


1.0.3
~~~~~

This is a maintenance release focusing on enhancements to the CI/CD pipeline, along with
minor fixes.

- BUILD: add the ``bcg_gamma`` conda channel when building
- BUILD: Enforce pre-release for minor and major releases
- DOC: add pre-commit hook instructions to contribution guide
- BUILD: update *flake8* to 3.9.0
- BUILD: apply make_base.py changes from 1.1.x also on develop (adds more robust parsing
  of package versions)
- FIX: version syntax adaptation with mixed ``=`` and ``>=``


1.0.2
~~~~~

This is a maintenance release focusing on enhancements to the CI/CD pipeline, along with
minor fixes.

- API: sort list of items returned by :meth:`.AllTracker.get_tracked`
- API: add protected method to class :class:`.MatplotStyle` to apply color scheme to
  :class:`~matplotlib.axes.Axes` object
- FIX: preserve correct instance for subclasses of singleton classes
- FIX: add a few missing type hints
- BUILD: add support for :mod:`numpy` 1.20
- BUILD: updates and changes to the CI/CD pipeline


1.0.1
~~~~~

Initial release.
