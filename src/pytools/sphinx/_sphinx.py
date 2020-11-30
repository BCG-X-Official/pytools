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
    Dict,
    ForwardRef,
    Generator,
    Generic,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
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
    "AutodocProcessDocstring",
    "AutodocBeforeProcessSignature",
    "AutodocProcessSignature",
    "AutodocSkipMember",
    "AddInheritance",
    "CollapseModulePaths",
    "CollapseModulePathsInDocstring",
    "CollapseModulePathsInSignature",
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

        Registered callbacks will be invoked on event in the order of priority and
        registration. The priority is ascending order.

        :param app: the Sphinx application to register this processor with
        :param priority: the priority of this processor
        :return: a listener ID that can be used as an argument to
            :meth:`~sphinx.application.Sphinx.disconnect`.
        """
        if priority is None:
            return app.connect(event=self.event, callback=self)
        else:
            return app.connect(event=self.event, callback=self, priority=priority)


class AutodocProcessDocstring(SphinxCallback, metaclass=ABCMeta):
    """
    An autodoc processor for docstrings.
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


class AutodocBeforeProcessSignature(SphinxCallback, metaclass=ABCMeta):
    """
    An autodoc processor invoked before processing signatures.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-before-process-signature"``
        """
        return "autodoc-before-process-signature"

    @abstractmethod
    def process(self, app: Sphinx, obj: object, bound_method: bool) -> None:
        """
        Process an event.

        :param app: the Sphinx application object
        :param obj: the object itself
        :param bound_method: a boolean indicates an object is bound method or not
        """
        pass

    def __call__(
        self, app: Sphinx, obj: object, bound_method: bool
    ) -> Optional[Tuple[str, str]]:
        try:
            return self.process(app=app, obj=obj, bound_method=bound_method)
        except Exception as e:
            log.error(e)


class AutodocProcessSignature(SphinxCallback, metaclass=ABCMeta):
    """
    An autodoc processor for processing signatures.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-process-signature"``
        """
        return "autodoc-process-signature"

    @abstractmethod
    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: Optional[str],
        return_annotation: Optional[str],
    ) -> Optional[Tuple[str, str]]:
        """
        Process an event.

        :param app: the Sphinx application object
        :param what: the type of the object which the docstring belongs to (one of
            "module", "class", "exception", "function", "method", "attribute")
        :param name: the fully qualified name of the object
        :param obj: the object itself
        :param options: the options given to the directive: an object with attributes
            ``inherited_members``, ``undoc_members``, ``show_inheritance`` and
            ``noindex`` that are ``True`` if the flag option of same name was given to
            the auto directive
        :param signature: function signature, as a string of the form
            ``(parameter_1, parameter_2)``, or ``None`` if introspection did not succeed
            and signature was not specified in the directive
        :param return_annotation: function return annotation as a string of the form
            `` -> <annotation>``, or ``None`` if there is no return annotation
        """
        pass

    def __call__(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: Optional[str],
        return_annotation: Optional[str],
    ) -> Optional[Tuple[str, str]]:
        try:
            return self.process(
                app=app,
                what=what,
                name=name,
                obj=obj,
                options=options,
                signature=signature,
                return_annotation=return_annotation,
            )
        except Exception as e:
            log.error(e)


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
class AddInheritance(AutodocProcessDocstring):
    """
    Add list of base classes as the first line of the docstring.

    Ignore builtin classes and classes that have already been visited once before.
    """

    def __init__(self, collapsible_submodules: Mapping[str, str]):
        """
        :param collapsible_submodules: mapping of submodule paths to shorter
            *(collapsed)* versions they should be replaced with
        """
        super().__init__()
        self.collapsible_submodules = collapsible_submodules

        #: dict mapping visited classes to their unprocessed docstrings
        self._visited: Dict[type, str] = {}

    F_BASES = ":bases:"  #: field directive for base classes
    F_GENERICS = ":generic types:"  #: field directive for generic types
    F_METACLASSES = ":metaclasses:"  #: field directive for metaclasses

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

            _current_lines = "\n".join(lines)
            try:
                _seen_lines = self._visited[class_]
                if _current_lines != _seen_lines:
                    # we are seeing another part of the docstring, probably in __init__
                    # vs. the class docstring;
                    # ignore this to prevent adding the same content at two places
                    return
            except KeyError:
                # we are seeing a class for the first time; store its content so we can
                # detect and allow repeat visits
                self._visited[class_] = _current_lines

            bases_with_origin = [
                (base, typing_inspect.get_origin(base) or base)
                for base in set(self._get_bases(class_, include_subclass=False))
            ]
            bases = [
                base
                for base, origin in bases_with_origin
                if not any(
                    origin is not other and issubclass(other, origin)
                    for _, other in bases_with_origin
                )
            ]

            bases_lines: List[str] = [""]
            if bases:
                base_names = (self._class_name_with_generics(base) for base in bases)
                bases_lines.append(f'{AddInheritance.F_BASES} {", ".join(base_names)}')

            generics: List[str] = self._get_generics(class_)
            if generics:
                bases_lines.append(f'{AddInheritance.F_GENERICS} {", ".join(generics)}')

            metaclasses: List[str] = self._get_metaclasses(class_)
            if metaclasses:
                bases_lines.append(
                    f'{AddInheritance.F_METACLASSES} {", ".join(metaclasses)}'
                )

            bases_lines.append("")

            # insert this after the intro text, and before class parameters

            def _insert_position() -> int:
                for n, line in enumerate(lines):
                    if re.match(r"\s*:\w+(?:\s+\w+)*:", line) and (
                        n == 0 or not line[n - 1].strip()
                    ):
                        return n
                return len(lines)

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
        module_name = AddInheritance._class_attr(
            cls=cls, attr="__module__", default=lambda: ""
        )

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

    @staticmethod
    def _class_name(cls: type) -> str:
        return AddInheritance._class_attr(
            cls=cls, attr="__qualname__", default=lambda: str(cls)
        )

    def _full_name(self, cls: type) -> str:
        # get the full name of the class, including the module prefix
        return f"{self._class_module(cls=cls)}.{self._class_name(cls=cls)}"

    def _class_name_with_generics(self, cls: Union[type, TypeVar]) -> str:
        def _class_tag(_name: Any) -> str:
            return f":class:`{str(_name)}`"

        if isinstance(cls, TypeVar):
            return _class_tag(cls)

        if isinstance(cls, ForwardRef):
            return _class_tag(cls.__forward_arg__)

        if not hasattr(cls, "__module__"):
            return _class_tag(cls)

        if cls.__module__ in ("__builtin__", "builtins"):
            return _class_tag(cls.__name__)

        else:
            generic_args = [
                self._class_name_with_generics(arg)
                for arg in typing_inspect.get_args(cls, evaluate=True)
            ]

            generic_arg_str = f' [{", ".join(generic_args)}]' if generic_args else ""

            return f":class:`~{self._full_name(cls)}`{generic_arg_str}"

    def _typevar_name(self, cls: TypeVar) -> str:
        if isinstance(cls, TypeVar):
            args: List[str] = [
                self._class_name_with_generics(c) for c in cls.__constraints__
            ]
            if cls.__bound__:
                args.append(f"bound= {self._class_name_with_generics(cls.__bound__)}")
            if cls.__covariant__:
                args.append("*__covariant__=True*")
            if cls.__contravariant__:
                args.append("*__contravariant__=True*")
            return f'{cls}({", ".join(args)})' if args else str(cls)
        else:
            return str(cls)

    def _get_bases(
        self, subclass: type, include_subclass: bool
    ) -> Generator[type, None, None]:
        # get the names of the immediate base classes of arg _subclass

        visited_classes: Set[type] = set()

        def _inner(
            _subclass: type, _include_subclass: bool
        ) -> Generator[type, None, None]:
            # ensure we have the non-generic origin class
            _subclass: type = typing_inspect.get_origin(_subclass) or _subclass

            if _subclass in visited_classes:
                return
            visited_classes.add(_subclass)

            # get the base classes; try generic bases first then fall back to regular
            # bases
            base_classes: Tuple[type] = (
                get_generic_bases(_subclass) or _subclass.__bases__
            )

            # include the _subclass itself in the list of bases, if requested
            if _include_subclass:
                # noinspection PyTypeChecker
                base_classes = (_subclass, *base_classes)

            # get the names of all base classes; go up the class hierarchy in case of
            # hidden classes
            for base in base_classes:

                # exclude object and Generic types
                if base is object or typing_inspect.get_origin(base) is Generic:
                    continue

                # exclude protected classes
                elif self._class_name(base).startswith("_"):
                    yield from _inner(base, _include_subclass=False)

                # all other classes will be listed as bases
                else:
                    yield base

        return _inner(subclass, _include_subclass=include_subclass)

    def _get_generics(self, child_class: type) -> List[str]:
        return list(
            itertools.chain.from_iterable(
                (
                    self._typevar_name(arg)
                    for arg in typing_inspect.get_args(base, evaluate=True)
                )
                for base in get_generic_bases(child_class)
                if typing_inspect.get_origin(base) is Generic
            )
        )

    def _get_metaclasses(self, class_: type) -> List[str]:
        return [
            self._class_name_with_generics(meta_)
            for meta_ in self._get_bases(type(class_), include_subclass=True)
            if meta_ is not type
        ]


class CollapseModulePaths(metaclass=ABCMeta):
    """
    Replace private module paths with their public prefix so that object references
    can be matched by *intersphinx*.
    """

    def __init__(
        self,
        collapsible_submodules: Mapping[str, str],
        collapse_private_modules: bool = True,
    ):
        """
        :param collapsible_submodules: mapping from module paths to their public
            prefix, e.g., ``{"pandas.core.frame": "pandas"}``
        :param collapse_private_modules: if ``True``, collapse module sub-paths
            consisting of one or more protected modules (i.e. the module name starts
            with an underscore)
        """
        super().__init__()
        self._classes_visited: Set[type] = set()

        col = [
            self._make_substitution_pattern(old.replace(".", r"\."), new)
            for old, new in collapsible_submodules.items()
        ]
        if collapse_private_modules:
            col.append(
                self._make_substitution_pattern(
                    r"(?P<module>(?:(?!_)\w+\.)+)(?:_\w*\.)*", r"\g<module>"
                )
            )

        self._intersphinx_collapsible_prefixes: List[Tuple[re.Pattern, str]] = col
        self._collapse_private_modules = collapse_private_modules

    @abstractmethod
    def _make_substitution_pattern(self, old: str, new: str) -> Tuple[re.Pattern, str]:
        # create the regex substitution rule given a raw match and replacement patterns
        pass

    def collapse_module_paths(self, line: Optional[str]) -> Optional[str]:
        """
        In the given line, replace all module paths with their collapsed version.

        :param line: the line in which to collapse module paths
        :return: the resulting line with collapsed module paths
        """
        if not line:
            return line

        for expanded, collapsed in self._intersphinx_collapsible_prefixes:
            line = expanded.sub(collapsed, line)

        return line


@inheritdoc(match="[see superclass]")
class CollapseModulePathsInDocstring(CollapseModulePaths, AutodocProcessDocstring):
    """
    Replace private module paths in docstrings with their public prefix so that object
    references can be matched by _intersphinx_.
    """

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

        for i, line in enumerate(lines):
            lines[i] = self.collapse_module_paths(line)

    def _make_substitution_pattern(self, old: str, new: str) -> Tuple[re.Pattern, str]:
        return re.compile(f"(`~?){old}"), f"\\1{new}"


@inheritdoc(match="[see superclass]")
class CollapseModulePathsInSignature(CollapseModulePaths, AutodocProcessSignature):
    """
    Replace private module paths in signatures with their public prefix so that object
    references can be matched by _intersphinx_.
    """

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: Optional[str],
        return_annotation: Optional[str],
    ) -> Optional[Tuple[str, str]]:
        """[see superclass]"""
        if signature or return_annotation:
            return (
                self.collapse_module_paths(signature),
                self.collapse_module_paths(return_annotation),
            )

    def _make_substitution_pattern(self, old: str, new: str) -> Tuple[re.Pattern, str]:
        return re.compile(old), new


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
