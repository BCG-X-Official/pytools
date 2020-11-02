"""
Implementation of sphinx module.
"""
import itertools
import logging
import re
from abc import ABCMeta, abstractmethod
from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    cast,
)

import typing_inspect

from pytools.api import AllTracker, get_generic_bases, inheritdoc

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "SphinxCallback",
    "AutodocLinesProcessor",
    "AutodocSkipMember",
    "AddInheritance",
    "CollapseModulePaths",
    "SkipIndirectImports",
]


#
# Type variables
#

#: Mock type declaration: Sphinx application object
Sphinx = Any


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class SphinxCallback(metaclass=ABCMeta):
    """
    Abstract base class for autodoc processors.

    Can be passed to :meth:`~sphinx.application.Sphinx.connect` as a callback for an
    event.
    """

    @property
    @abstractmethod
    def event(self) -> str:
        """
        The event processed by this callback.

        Used to connect this callback to sphinx in method :meth:`.connect`.

        :return: name of the event
        """
        pass

    def connect(self, app: Sphinx, priority: Optional[int] = None) -> int:
        """
        Register this callback to be called when :attr:`.event` is emitted.

        :param app:
        :param priority:
        :return: a "listener ID" that can be used as an argument to \
            :meth:`~sphinx.application.Sphinx.disconnect`.
        """
        if priority is None:
            return app.connect(event=self.event, callback=self)
        else:
            return app.connect(event=self.event, callback=self, priority=priority)


class AutodocLinesProcessor(SphinxCallback, metaclass=ABCMeta):
    """
    An autodoc processor for processing lines.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-process-docstring"``
        """
        return "autodoc-process-docstring"

    @abstractmethod
    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: List[str],
    ) -> None:
        """
        Process an event.

        :param app: the Sphinx application object
        :param what: the type of the object which the docstring belongs to (one of \
            "module", "class", "exception", "function", "method", "attribute")
        :param name: the fully qualified name of the object
        :param obj: the object itself
        :param options: the options given to the directive: an object with attributes \
            ``inherited_members``, ``undoc_members``, ``show_inheritance`` and \
            ``noindex`` that are ``True`` if the flag option of same name was given to \
            the auto directive
        :param lines: the lines of the docstring
        """
        pass

    def __call__(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: List[str],
    ) -> None:
        try:
            self.process(
                app=app, what=what, name=name, obj=obj, options=options, lines=lines
            )
        except Exception as e:
            log.error(e)
            raise


class AutodocSkipMember(SphinxCallback, metaclass=ABCMeta):
    """
    An autodoc-skip-member processor.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-skip-member"``
        """
        return "autodoc-skip-member"

    @abstractmethod
    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        skip: bool,
        options: object,
    ) -> Optional[bool]:
        """
        Decide whether a member should be included in the documentation.

        :param app: the Sphinx application object
        :param what: the type of the object which the docstring belongs to (one of \
            "module", "class", "exception", "function", "method", "attribute")
        :param name: the fully qualified name of the object
        :param obj: the object itself
        :param skip: a boolean indicating if autodoc will skip this member if the user \
            handler does not override the decision
        :param options: the options given to the directive: an object with attributes \
            ``inherited_members``, ``undoc_members``, ``show_inheritance`` and \
            ``noindex`` that are ``True`` if the flag option of same name was given to \
            the auto directive
        :return: ``True`` if the member should be excluded; ``False`` if the member \
            should be included; ``None`` to fall back to the skipping behavior of \
            autodoc and other enabled extensions


        """
        pass

    def __call__(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        skip: bool,
        options: object,
    ) -> Optional[bool]:
        try:
            return self.process(
                app=app, what=what, name=name, obj=obj, skip=skip, options=options
            )
        except Exception as e:
            log.error(e)
            raise


@inheritdoc(match="[see superclass]")
class AddInheritance(AutodocLinesProcessor):
    """
    Add list of base classes as the first line of the docstring. Ignore builtin
    classes and classes that were already visited once
    """

    def __init__(self, collapsible_submodules: Mapping[str, str]):
        super().__init__()
        self.collapsible_submodules = collapsible_submodules

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: List[str],
    ) -> None:
        """[see superclass]"""

        if what == "class":

            # add bases and generics documentation to class

            # generate the RST for bases and generics
            class_ = cast(type, obj)

            bases_with_origin = [
                (base, typing_inspect.get_origin(base) or base)
                for base in set(self._get_bases(class_))
            ]
            bases = [
                base
                for base, origin in bases_with_origin
                if not any(
                    origin is not other and issubclass(other, origin)
                    for _, other in bases_with_origin
                )
            ]

            bases_lines = [""]
            if bases:
                base_names = (self._class_name_with_generics(base) for base in bases)
                bases_lines.append(f'Bases: {", ".join(base_names)}')
                bases_lines.append("")

            generics: List[str] = self._get_generics(class_)
            if generics:
                generic_type_variables = f'Generic types: {", ".join(generics)}'
                bases_lines.append(generic_type_variables)
                bases_lines.append("")

            # insert this after the intro text, and before class parameters

            def _insert_position() -> int:
                for n, line in enumerate(lines):
                    if re.match(r"\s*:param\s*\w+:", line):
                        return n
                return -1

            if len(bases_lines) > 0:
                pos = _insert_position()
                lines[pos:pos] = bases_lines

    @staticmethod
    def _class_attr(cls: type, attr: str, default: Callable[[], str]) -> str:
        def _get_attr(_cls: type) -> str:
            try:
                # we try to get the class name
                return getattr(_cls, attr)
            except AttributeError:
                # if the name is not defined, this class is likely to have generic
                # arguments, so we re-try recursively with the origin (unless the origin
                # is the class itself to avoid infinite recursion)
                cls_origin = typing_inspect.get_origin(cls)
                if cls_origin != _cls:
                    return _get_attr(_cls=cls_origin)
                else:
                    # as a last resort, we convert the class to a string
                    return default()

        return _get_attr(_cls=cls)

    def _class_module(self, cls: type) -> str:
        module_name = self._class_attr(cls=cls, attr="__module__", default=lambda: "")

        collapsed_module = self.collapsible_submodules.get(module_name, None)
        if collapsed_module:
            return collapsed_module

        # remove private submodules
        module_path = module_name.split(".")
        for i, submodule in enumerate(module_path):
            if submodule.startswith("_"):
                return ".".join(module_path[:i])

        # return the unchanged module name
        return module_name

    def _class_name(self, cls: type) -> str:
        return self._class_attr(cls=cls, attr="__qualname__", default=lambda: str(cls))

    def _full_name(self, cls: type) -> str:
        # get the full name of the class, including the module prefix
        return f"{self._class_module(cls=cls)}.{self._class_name(cls=cls)}"

    def _class_name_with_generics(self, cls: type) -> str:
        if not hasattr(cls, "__module__"):
            return str(cls)

        if cls.__module__ in ("__builtin__", "builtins"):
            return f":class:`{cls.__name__}`"

        else:
            generic_args = [
                self._class_name_with_generics(arg)
                for arg in typing_inspect.get_args(cls, evaluate=True)
            ]

            generic_arg_str = f' [{", ".join(generic_args)}]' if generic_args else ""

            return f":class:`~{self._full_name(cls)}`{generic_arg_str}"

    def _get_bases(self, child_class: type) -> Generator[type, None, None]:
        # get the names of the immediate base classes of arg child_class

        # ensure we have the non-generic origin class
        child_class = typing_inspect.get_origin(child_class) or child_class

        # get the base classes; try generic bases first then fall back to regular bases
        base_classes = get_generic_bases(child_class) or child_class.__bases__

        # get the names of all base classes; go up the class hierarchy in case of hidden
        # classes
        for base in base_classes:

            # exclude object and Generic types
            if base is object or typing_inspect.get_origin(base) is Generic:
                continue

            # exclude protected classes
            elif self._class_name(base).startswith("_"):
                yield from self._get_bases(base)

            # all other classes will be listed as bases
            else:
                yield base

    def _get_generics(self, child_class: type) -> List[str]:
        return list(
            itertools.chain.from_iterable(
                (
                    [
                        self._class_name_with_generics(arg)
                        for arg in typing_inspect.get_args(base, evaluate=True)
                    ]
                    for base in get_generic_bases(child_class)
                    if typing_inspect.get_origin(base) is Generic
                )
            )
        )


@inheritdoc(match="[see superclass]")
class CollapseModulePaths(AutodocLinesProcessor):
    """
    Replace private module paths with their public prefix so that object references
    can be matched by _intersphinx_.
    """

    def __init__(self, collapsible_submodules: Mapping[str, str]):
        """
        :param collapsible_submodules: mapping from module paths to their public \
            prefix, e.g., ``{"pandas.core.frame": "pandas"}``
        """
        super().__init__()
        self._classes_visited: Set[type] = set()

        self._intersphinx_collapsible_prefixes: List[Tuple[re.Pattern, str]] = [
            *[
                (re.compile(r"(`~?)" + old.replace(".", r"\.")), f"\\1{new}")
                for old, new in collapsible_submodules.items()
            ],
            (re.compile(r"(`~?(?:(?!_)\w+\.)+)(_\w*\.)+"), r"\1"),
        ]

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: List[str],
    ) -> None:
        """[see superclass]"""

        for expanded, collapsed in self._intersphinx_collapsible_prefixes:
            for i, line in enumerate(lines):
                lines[i] = expanded.sub(collapsed, line)


@inheritdoc(match="[see superclass]")
class SkipIndirectImports(AutodocSkipMember):
    """
    Skip members imported by a private package.
    """

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        skip: bool,
        options: object,
    ) -> Optional[bool]:
        """[see superclass]"""
        if not skip:
            if what == "module" and name.startswith("_"):
                log.info(f"skipping: {what}: {name}")
                return False


__tracker.validate()
