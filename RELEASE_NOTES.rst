Release Notes
=============

.. |mypy| replace:: :external+mypy:doc:`mypy <index>`
.. |nbsp| unicode:: 0xA0
   :trim:

*pytools* 3.0
-------------

*pytools* 3.0 adds support for language features introduced up to and including
Python 3.10, and drops support for Python versions.

*pytools* 3.0.1
~~~~~~~~~~~~~~~

- BUILD: add support for Python 3.10


*pytools* 3.0.0
~~~~~~~~~~~~~~~

- :mod:`pytools.api`: new utility functions to get object's init parameters, validate
  ``__all__`` declarations, and define stand-in objects for missing classes and
  functions

    - API: new function :func:`.get_init_params` to retrieve the object attributes
      associated with the object's ``__init__`` method
    - API: new metaclass :class:`MissingClassMeta` to define a stand-in class for a
      missing class that could not be imported from an optional dependency
    - API: new function :func:`.missing_function` to define a stand-in function for a
      missing function that could not be imported from an optional dependency
    - API: new function :func:`.validate__all__declarations` to validate the ``__all__``
      declarations of a module and its submodules

- :mod:`pytools.asyncio`: new module with utility functions for asynchronous programming

  - :func:`.arun` to run an asynchronous function in a new event loop
  - :func:`.aenumerate` to enumerate an asynchronous iterable
  - :func:`.async_flatten` to flatten nested asynchronous iterables for optimized
    asynchronous processing
  - :func:`.iter_async_to_sync` to convert an asynchronous iterable to a synchronous
    one
  - :func:`.iter_sync_to_async` to convert a synchronous iterable to an asynchronous
    one
  - :func:`.unpack_exception_group` to unpack an exception group into one or more
    individual exceptions

- :mod:`pytools.data.taxonomy`: new submodule with classes :class:`.Taxonomy` and
  :class:`.Category` to represent hierarchical taxonomies

- :mod:`pytools.expression`:

  - new function :func:`.expression_from_init_params` to create an object's
    :class:`.Expression` representation from the attributes in its ``__init__`` method
  - new submodule :mod:`pytools.expression.repr` with enhanced versions of standard
    Python container classes implementing the :class:`.HasExpressionRepr` interface:

    - :class:`.ListWithExpressionRepr` for lists
    - :class:`.TupleWithExpressionRepr` for tuples
    - :class:`.SetWithExpressionRepr` for sets
    - :class:`.DictWithExpressionRepr` for dictionaries

- :mod:`pytools.http`: new module with function :func:`.fetch_url` to download a file
  from a URL

- :mod:`pytools.repr`: new module with mixin class :class:`.HasDictRepr`, providing a
  method to return a dictionary representation of an object

- :mod:`pytools.sphinx`: new utilities for generating Sphinx documentation

  - API: new decorator :obj:`.apenddoc` to append docstrings to the docstring of another
    object, usually the constructor of the superclass
  - API: new Sphinx callback class :class:`.ResolveTypeVariables` to resolve type
    variables in attribute signatures

- :mod:`pytools.text`: new class :class:`.TextTemplate` to generate text from a template
  string with stricter management of template variables

- :mod:`pytools.typing`: new module for generic type inspection at runtime

  - new function :func:`.get_common_generic_base` to retrieve the common generic base
    class of two types
  - new function :func:`.get_common_generic_subclass` to retrieve the common generic
    subclass of two types
  - new function :func:`~pytools.typing.get_generic_bases` to retrieve the generic base
    classes of a type
  - new function :func:`.get_generic_instance` to retrieve the generic instance of a
    type
  - new function :func:`.get_type_arguments` to retrieve the type arguments of a generic
    type
  - new function :func:`.isinstance_generic` to check if an object is an instance of a
    generic type
  - new function :func:`.issubclass_generic` to check if a type is a subclass of a
    generic type

- :mod:`pytools.viz`:

  - API: new class :class:`.HTMLStyle` for rendering HTML content with drawers
  - API: new function :func:`.is_running_in_notebook` to check if the code is running
    in a Jupyter or Colab notebook
  - API: new property :attr:`.RgbColor.hex` and :attr:`.RgbaColor.hex` to
    return the color as a hexadecimal string

- Various adjustments to maintain compatibility with recent Python versions


*pytools* 2.1
-------------

2.1.3
~~~~~

- FIX: :class:`.DendrogramMatplotStyle` now calls :meth:`.Axis.set_ticklabels` using a
  positional argument for the labels, to address a change in *matplotlib* |nbsp| 3.7


2.1.2
~~~~~

This is a maintenance release to catch up with *pytools* |nbsp| 2.0.7.


2.1.1
~~~~~

- API: :class:`.AllTracker` now resolves forward references in type aliases
  exported via ``__all__``


2.1.0
~~~~~

- API: new decorator :obj:`.fitted_only` to mark methods that may only be
  called after their associated object has been fitted using :meth:`.FittableMixin.fit`
- API: remove method ``ensure_fitted`` from :class:`.FittableMixin`, which is no longer
  needed due to the new decorator :obj:`.fitted_only`.
- API: new Sphinx callback :class:`.TrackCurrentClass` to keep track of the current
  class being processed by *autodoc*.
- API: new Sphinx callback :class:`.RenamePrivateArguments` to rename private
  “positional-only” arguments in a function's signature (with two leading underscores)
  back to their original names in the source code, so that *autodoc* can pick them up
  correctly.
- API: :class:`.Expression` objects support plain text and HTML output in Jupyter
  notebooks


*pytools* 2.0
-------------

*pytools* 2 introduces enhanced visualisations along with additional API improvements,
and is now subject to static type checking with |mypy|.

2.0.7
~~~~~

- FIX: prevent `matplot` warnings about missing fonts when rendering drawers using the :class:`.MatplotStyle`


2.0.6
~~~~~

- BUILD: add support for :mod:`pandas` |nbsp| 2.0 and above


2.0.5
~~~~~

- API: de-dent docstrings before processing them with the :obj:`.subsdoc` decorator
- FIX: in method :meth:`.AllTracker.resolve_forward_references`, unwrap functions before
  accessing their ``__globals__`` attribute


2.0.4
~~~~~

- FIX: make :meth:`.MatplotStyle.get_renderer()` compatible with
  :mod:`matplotlib` |nbsp| 3.6


2.0.3
~~~~~

- REFACTOR: rename arg of :meth:`.FittableMixin.fit` to ``__x``, so that |mypy|
  recognizes it as a positional-only argument, and that subclasses can change its
  name without breaking the API
- FIX: make :class:`.ResolveTypeVariables` compatible with Python |nbsp| 3.9
- FIX: recognise private (positional-only) arguments in :class:`.DocValidator`
- DOC: show original names of private (positional-only) arguments in Sphinx
  documentation, not their substituted private names generated by Python


2.0.2
~~~~~

- REFACTOR: run *mypy* type checks in *strict* mode
- FIX: more reliably determine the class when resolving type variables for Sphinx API
  documentation
- FIX: no longer raise an exception when attempting to get the class name for
  :obj:`~typing.Union` and other “special” types


2.0.1
~~~~~

- FIX: in class :class:`.AllTracker`, do not attempt to update forward references in
  imported objects
- BUILD: update build scripts to support the stricter dependency resolver introduced by
  *pip* |nbsp| 20.3, and to fix a compatibility issue with recent updates to nbsphinx
- BUILD: enable local sphinx builds in other FACET packages
- DOC: simplify how the docs build manages existing documentation of previous versions
  in the Azure pipeline and the associated commands in `make.py`:
  under the new approach, documentation is only preserved for the latest patch of each
  minor version, reducing the amount of near-similar documentation
- DOC: use pydata sphinx theme v0.9 (but disable dark mode)


2.0.0
~~~~~

``pytools.api``
^^^^^^^^^^^^^^^

- API: collection validation/conversion functions :func:`.to_set`, :func:`.to_tuple`,
  :func:`.to_list`, and :func:`.to_collection` have a new argument ``optional``
- API: decorator :func:`.subsdoc` has a new optional argument ``using``, indicating
  an object whose docstring will be used as the basis for creating the substituted
  docstring of the decorated object

``pytools.data``
^^^^^^^^^^^^^^^^

- API: new class :class:`.Matrix` allows :class:`.MatrixDrawer` to render flexible row
  and column widths, based on the :attr:`.Matrix.weights` property, and supports axis
  labels for the row, column, and weight axes
- API: moved class :class:`.LinkageTree` to module :mod:`pytools.data`

``pytools.expression``
^^^^^^^^^^^^^^^^^^^^^^

- API: improved conversion of :mod:`numpy` arrays to :class:`.Expression` objects in
  function :func:`.make_expression`
- API: removed method ``get_class_id`` from class :class:`.HasExpressionRepr`

``pytools.fit``
^^^^^^^^^^^^^^^

- API: method :meth:`.FittableMixin.ensure_fitted` is now public, replacing the formerly
  private method ``_ensure_fitted()``

``pytools.meta``
^^^^^^^^^^^^^^^^

- API: removed function ``compose_meta`` due to conflicts with *mypy* static type checks
- API: new metaclass :class:`.SingletonABCMeta` combining :class:`.SingletonMeta` and
  :class:`~abc.ABCMeta`

``pytools.parallelization``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- API: method :meth:`.JobRunner.run_jobs` now expects a single iterable of :class:`.Job`
  objects instead of individual jobs as positional arguments
- API: method :meth:`.JobRunner.run_queues` now expects a single iterable of
  :class:`.JobQueue` objects instead of individual queues as positional arguments, and
  returns a :class:`list` of results instead of an iterator
- API: methods :meth:`.JobRunner.run_queue` and :meth:`.JobRunner.run_queues` are now
  thread-safe
- API: renamed method ``collate`` of class :class:`.JobQueue` to
  :meth:`.JobQueue.aggregate`
- API: :class:`.SimpleQueue` is now an abstract class, expecting subclasses to implement
  method :meth:`.SimpleQueue.aggregate`
- API: renamed class ``NestedQueue`` to :class:`.CompositeQueue`

``pytools.sphinx``
^^^^^^^^^^^^^^^^^^

- API: new Sphinx callback class :class:`.ObjectDescriptionTransform`

- API: renamed callback class ``ResolveGenericClassParameters`` to
  :class:`.ResolveTypeVariables` and updated to resolve type variables also in
  attribute signatures

``pytools.text``
^^^^^^^^^^^^^^^^

- API: new function :func:`.camel_case_to_snake_case`

``pytools.viz``
^^^^^^^^^^^^^^^

Additions and enhancements to dendrogram and matrix visualizations.

- **Dendrograms:** major design overhaul

  - API: replaced the heatmap and line dendrogram styles with a single, freshly designed
    :class:`.DendrogramMatplotStyle` offering a tighter layout and using the thickness
    of the dendrogram's branches to indicate the cumulative weight of the leaf nodes
  - API: :attr:`.DendrogramMatplotStyle.padding` determines the adjustable padding
    between neighbouring branches; setting padding to zero produces a chart similar
    to the previous *heatmap* style
  - API: :class:`.DendrogramDrawer` no longer sorts leaf nodes as part of the drawing
    process; the sorting mechanism is now available via method
    :meth:`.LinkageTree.sort_by_weight`
  - VIZ: :class:`.DendrogramMatplotStyle` and :class:`.DendrogramReportStyle` now render
    leaves in left-to-right order, instead of the previous right-to-left order
  - API: the :class:`.DendrogramReportStyle` now reduces the label section of the
    dendrogram to the length of the longest label; renamed the ``label_width``
    property to :attr:`~.DendrogramReportStyle.max_label_width`
  - API: moved class :class:`.LinkageTree` to module :mod:`pytools.data`
  - API: new method :meth:`.LinkageTree.iter_nodes` for depth-first traversal of
    the linkage tree

- **Matrices:** major design overhaul

  - API: class :class:`.MatrixDrawer` now expects instances of new class
    :class:`.Matrix` as its input
  - API: :class:`.MatrixDrawer` no longer accepts :class:`~pandas.DataFrame`
    objects, but :meth:`.Matrix.from_frame` can be used to convert data frames
    to matrix objects
  - API: new attribute :attr:`.MatrixMatplotStyle.nan_substitute` specifies the value to
    look up in the colormap to determine the color of undefined matrix cells
  - VIZ: :class:`.MatrixMatplotStyle` enforces a 1:1 |nbsp| aspect ratio for the row and
    column axes, so that equal row and column widths represent equal weights

- API: new public method :meth:`.Drawer.get_style_kwargs`, replacing the previously
  private method ``_get_style_kwargs()``

- API: implement :class:`.RgbColor` and :class:`.RgbaColor` as classes instead of
  type aliases

- API: removed method ``dark()`` from class :class:`.ColoredStyle` and instead introduce
  constants :attr:`.ColorScheme.DEFAULT`, :attr:`.ColorScheme.DEFAULT_LIGHT`, and
  :attr:`.ColorScheme.DEFAULT_DARK`


*pytools* 1.2
-------------

1.2.5
~~~~~

This is a maintenance release to catch up with *pytools* |nbsp| 1.1.10.


1.2.4
~~~~~

This is a maintenance release to catch up with *pytools* |nbsp| 1.1.8.


1.2.3
~~~~~

This release enhances support for generating Sphinx documentation, and catches up with
*pytools* |nbsp| 1.1.7.

- API: add sphinx processor :class:`.ResolveGenericClassParameters`
  to substitute generic type parameters introduced by base classes or via the
  ``self`` and ``cls`` special method arguments
- API: add sphinx processor :class:`.AutodocProcessBases` to handle
  `autodoc-process-bases` events (introduced in Sphinx |nbsp| 4.1)
- API: function :func:`.validate_type` now accepts multiple alternative types to
  validate values against, in line with how :func:`isinstance` tests for multiple types


1.2.2
~~~~~

This is a maintenance release to catch up with *pytools* |nbsp| 1.1.5.


1.2.1
~~~~~

This is a maintenance release to catch up with *pytools* |nbsp| 1.1.4.


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
  *pytools* |nbsp| 1.1.7


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
- FIX: calling method ``get_class_id`` of class :class:`.Id` could cause a
  :class:`.TypeError`
- FIX: :class:`.Replace3rdPartyDoc` sphinx callback now substitutes 3rd-party docstrings
  also for :class:`.property` definitions


1.1.5
~~~~~

- FIX: fixed a rare case where :meth:`.Expression.eq_` returned ``False`` for two
  equivalent expressions if one of them included an :class:`.ExpressionAlias`
- FIX: accept any type of numerical values as leaf weights of :class:`.LinkageTree`


1.1.4
~~~~~

- BUILD: add support for :mod:`joblib` |nbsp| 1.0.*


1.1.3
~~~~~

- FIX: comparing two :class:`.InfixExpression` objects using method
  :meth:`.Expression.eq_` would erroneously yield ``True`` if both expressions
  had the same operator but a different number of operands, and the operands of the
  shorter expression were equal to the operands at the start of the longer expression


1.1.2
~~~~~

- Catch up with fixes and pipeline updates introduced by *pytools* |nbsp| 1.0.3 and
  |nbsp| 1.0.4
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

- FIX: back-port *pytools* |nbsp| 1.1 bugfix for :meth:`.Expression.eq_`


1.0.5
~~~~~

- FIX: back-port *pytools* |nbsp| 1.1 bugfix for building multi-version documentation


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
- BUILD: update *flake8* to |nbsp| 3.9.0
- BUILD: apply make_base.py changes from |nbsp| 1.1.x also on develop (adds more robust parsing
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
- BUILD: add support for :mod:`numpy` |nbsp| 1.20
- BUILD: updates and changes to the CI/CD pipeline


1.0.1
~~~~~

Initial release.
