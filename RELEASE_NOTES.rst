Release Notes
=============

*pytools* 1.0
-------------

1.1.0
~~~~~

- API: AllTracker detects and prohibits exporting objects imported from other modules
- API: AllTracker detects and prohibits exporting global constants (the preferred
       approach is to define constants inside classes as this provides better context,
       and will be properly documented via Sphinx)


*pytools* 1.0
-------------

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
