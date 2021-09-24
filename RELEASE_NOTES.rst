Release Notes
=============

*pytools* 2.0
-------------

2.0.0
~~~~~

- API: additions and enhancements to visualizations in module :mod:`pytools.viz`, and
  related classes in module :mod:`.pytools.data`

    - *Dendrograms:* major design overhaul

      - replaced the heatmap and line dendrogram styles with a single, freshly designed
        :class:`.DendrogramMatplotStyle` which
          - varies the thickness of the dendrogram's branches, based on the cumulative
            weight of the leaf nodes
          - supports adjustable padding between neighbouring branches; setting padding
            to zero produces a chart that is close to the previous *heatmap* style

      - :class:`.DendrogramDrawer` no longer sorts leaf nodes inside as part of the
        drawing process; the sorting mechanism is now available via method
        :meth:`.LinkageTree.sort_by_weight`
      - flipped dendrograms along the leaves axis: :class:`.DendrogramMatplotStyle`
        and :class:`.DendrogramReportStyle` now render leaves in left-to-right order,
        instead of the previous right-to-left order
      - :class:`DendrogramReportStyle` now reduces the label section of the
        dendrogram to the length of the longest label; renamed the `label_width`
        property to `max_label_width`
      - moved class :class:`.LinkageTree` to module :mod:`pytools.viz`
      - new method :meth:`.LinkageTree.iter_nodes` for depth-first traversal of
        a linkage tree

    - *Matrices:* major design overhaul

        - class :class:`.MatrixDrawer` now expects instances of new class
          :class:`.Matrix` as its input
          - class :class:`.Matrix` allows :class:`.MatrixDrawer` to render
            flexible row and column widths, based on the :attr:`.Matrix.weights`
            property, and supports axis labels for the row, column, and weight axes
          - :class:`.MatrixDrawer` no longer accepts :class:`~pandas.DataFrame`
            objects, but :meth:`.Matrix.from_frame` can be used to convert data frames
            to matrix objects
        - new attribute :class:`.MatrixDrawer.nan_substitute` specifies the value to
          look up in the colormap to determine the color of undefined matrix cells
        - :class:`.MatrixMatplotStyle` enforces a 1:1 aspect ratio for the row and
          column axes, so that equal row and column widths represent equal weights


- API: revised job/queue API in module :mod:`pytools.parallelization`

    - method :meth:`.JobRunner.run_jobs` now expects a single iterable of :class:`.Job`
      objects instead of individual jobs as positional arguments

    - method :meth:`.JobRunner.run_queues` now expects a single iterable of
      :class:`.JobQueue` objects instead of individual queues as positional arguments

    - method :meth:`.JobRunner.run_queues` returns a list of results instead of an
      iterator

    - methods :meth:`.JobRunner.run_queue` and :meth:`.JobRunner.run_queues` are now
      thread-safe

    - rename method `collate` of class :class:`.JobQueue` to :meth:`.JobQueue.aggregate`

    - :class:`.SimpleQueue` is now an abstract class, expecting subclasses to implement
      method :meth:`.SimpleQueue.aggregate`

- API: improved conversion of *numpy* arrays to :class:`.Expression` objects in
  function :func:`.make_expression`


*pytools* 1.2
-------------

1.2.3
~~~~~

This release enhances support for generating Sphinx documentation, and catches up with
*pytools* 1.1.6.

- API: add sphinx processor :class:`.ResolveGenericClassParameters`
  to resolve generic type parameters in subclasses
- API: add sphinx processor :class:`.AutodocProcessBases` to handle
  `autodoc-process-bases` events (introduced in Sphinx 4.1)


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
- BUILD: add support for `matplotlib >= 3.4`, `scipy >= 1.6`,
  and `typing-inspect == 0.7`


*pytools* 1.1
-------------

1.1.6
~~~~~

- FIX: ensure correct weight labels when rendering dendrograms as plain text using the
  :class:`.DendrogramReportStyle`
- FIX: calling method :meth:`.Id.get_class_id` could cause a :class:`.TypeError`
- VIZ: set colors of axis labels to the foreground color of the current color scheme


1.1.5
~~~~~

- FIX: fixed a rare case where :meth:`.Expression.eq_` returned `False` for two
  equivalent expressions if one of them included an :class:`.ExpressionAlias`
- FIX: accept any type of numerical values as leaf weights of :class:`.LinkageTree`


1.1.4
~~~~~

- BUILD: allow `joblib` 1.0.* in joblib package requirements


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
