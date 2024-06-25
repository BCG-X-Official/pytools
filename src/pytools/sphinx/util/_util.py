"""
Implementation of sphinx utility callbacks specific to building Gamma documentation.
"""

from __future__ import annotations

import collections.abc
import importlib
import itertools
import logging
import re
import typing
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Generator, Iterable, Mapping
from inspect import getattr_static
from re import Pattern
from types import FunctionType, GenericAlias, MethodType, UnionType
from typing import Any, ForwardRef, Generic, TypeVar, Union, cast, get_type_hints

import typing_inspect

from ...api import (
    AllTracker,
    inheritdoc,
    public_module_prefix,
    subsdoc,
    update_forward_references,
)
from ...meta import SingletonABCMeta
from .. import (
    AutodocBeforeProcessSignature,
    AutodocProcessDocstring,
    AutodocProcessSignature,
    AutodocSkipMember,
    ObjectDescriptionTransform,
)

try:
    # import sphinx classes if available ...
    from docutils.nodes import Element, Text
    from sphinx.application import Sphinx
except ImportError:
    # ... otherwise mock them up

    # noinspection PyMissingOrEmptyDocstring,PyUnusedLocal,SpellCheckingInspection
    class _Element:
        children: list[Element]
        attributes: dict[str, Any]

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise TypeError("docutils package is not installed")

        def replace(self, old: Element, new: Element) -> None: ...  # noqa: E704

    # noinspection PyMissingOrEmptyDocstring,SpellCheckingInspection
    class _Text(_Element):
        rawsource: str

        # noinspection SpellCheckingInspection
        def astext(self) -> str:  # type: ignore
            ...

    Sphinx = type("Sphinx", (object,), {})
    Element = _Element
    Text = _Text


#
# Constants
#


log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "AddInheritance",
    "CollapseModulePaths",
    "CollapseModulePathsInDocstring",
    "CollapseModulePathsInSignature",
    "CollapseModulePathsInXRef",
    "RenamePrivateArguments",
    "Replace3rdPartyDoc",
    "ResolveTypeVariables",
    "SkipIndirectImports",
    "TrackCurrentClass",
    "UpdateForwardReferences",
]

#
# Type variables
#

method_descriptor: type[Any] = type(str.startswith)
wrapper_descriptor: type[Any] = type(str.__add__)
internal_function_or_method: type[Any] = type(iter)


#
# Constants
#

METHOD_TYPE_DYNAMIC = 0
METHOD_TYPE_STATIC = 1
METHOD_TYPE_CLASS = 2


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


@inheritdoc(match="""[see superclass]""")
class AddInheritance(AutodocProcessDocstring):
    """
    Add list of base classes as the first line of the docstring.

    Ignore builtin classes and classes that have already been visited once before.
    """

    def __init__(self, collapsible_submodules: Mapping[str, str]) -> None:
        """
        :param collapsible_submodules: mapping of submodule paths to shorter
            *(collapsed)* versions they should be replaced with
        """
        super().__init__()
        self.collapsible_submodules = collapsible_submodules

        #: Dict mapping visited classes to their unprocessed docstrings.
        self._visited: dict[type, str] = {}

    #: Field directive for base classes.
    F_BASES = ":bases:"
    #: Field directive for generic types.
    F_GENERICS = ":generic types:"
    #: Field directive for metaclasses.
    F_METACLASSES = ":metaclasses:"

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: list[str],
    ) -> None:
        """[see superclass]"""

        if what != "class":
            return

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
            # we are seeing a class for the first time; store its content, so we can
            # detect and allow repeat visits
            self._visited[class_] = _current_lines

        bases_lines: list[str] = [""]

        bases: list[type] = _get_minimal_bases(class_)
        if bases:
            base_names = (self._class_name_with_generics(base) for base in bases)
            bases_lines.append(f'{AddInheritance.F_BASES} {", ".join(base_names)}')

        generics: list[str] = self._get_generics(class_)
        if generics:
            bases_lines.append(f'{AddInheritance.F_GENERICS} {", ".join(generics)}')

        metaclasses: list[str] = self._get_metaclasses(class_)
        if metaclasses:
            bases_lines.append(
                f'{AddInheritance.F_METACLASSES} {", ".join(metaclasses)}'
            )

        bases_lines.append("")

        # insert this after the intro text, and before class parameters

        self._insert_bases_lines(bases_lines, lines)

    @staticmethod
    def _insert_bases_lines(bases_lines: list[str], lines: list[str]) -> None:
        def _insert_position() -> int:
            for n, line in enumerate(lines):
                if re.match(r"\s*:\w+(?:\s+\w+)*:", line) and (
                    n == 0 or not lines[n - 1].strip()
                ):
                    return n
            return len(lines)

        if len(bases_lines) > 0:
            pos = _insert_position()
            lines[pos:pos] = bases_lines

    def _class_module(self, cls: type) -> str:
        module_name: str = public_module_prefix(cls.__module__)

        # return the collapsed submodule if it exists,
        # else return the unchanged module name
        return self.collapsible_submodules.get(module_name, module_name)

    def _full_name(self, cls: type) -> str:
        # get the full name of the class, including the module prefix
        return f"{self._class_module(cls)}.{_class_name(cls)}"

    def _class_name_with_generics(self, cls: Any) -> str:
        def _class_tag(
            name: str,
            *,
            is_class: bool = True,
            is_local: bool = False,
            is_short: bool = False,
        ) -> str:
            if is_local:
                name = f".{name}"
            if is_short:
                name = f"~{name}"
            if is_class:
                return f":class:`{name}`"
            else:
                return f":obj:`{name}`"

        if isinstance(cls, TypeVar):
            return str(cls)

        if isinstance(cls, ForwardRef):
            if cls.__forward_evaluated__:
                cls = cls.__forward_value__
            else:
                return _class_tag(cls.__forward_arg__, is_local=True)

        if not hasattr(cls, "__module__"):
            return _class_tag(str(cls))

        if cls.__module__ in ("__builtin__", "builtins"):
            return _class_tag(cls.__name__)

        else:
            generic_args = [
                self._class_name_with_generics(arg)
                for arg in typing_inspect.get_args(cls, evaluate=True)
            ]

            generic_arg_str = f" [{', '.join(generic_args)}]" if generic_args else ""

            return (
                _class_tag(
                    self._full_name(cls), is_class=isinstance(cls, type), is_short=True
                )
                + generic_arg_str
            )

    def _typevar_name(self, cls: TypeVar) -> str:
        if isinstance(cls, TypeVar):
            args: list[str] = [
                self._class_name_with_generics(c)
                for c in getattr(cls, "__constraints__", ())
            ]
            if getattr(cls, "__bound__", None):
                args.append(f"bound= {self._class_name_with_generics(cls.__bound__)}")
            return f'{cls}({", ".join(args)})' if args else str(cls)
        else:
            return str(cls)

    def _get_generics(self, child_class: type) -> list[str]:
        return list(
            itertools.chain.from_iterable(
                (
                    self._typevar_name(arg)
                    for arg in typing_inspect.get_args(base, evaluate=True)
                )
                for base in _get_generic_bases(child_class)
                if typing_inspect.get_origin(base) is Generic
            )
        )

    def _get_metaclasses(self, class_: type) -> list[str]:
        return [
            self._class_name_with_generics(meta_)
            for meta_ in _get_bases(type(class_), include_subclass=True)
            if meta_ is not type
        ]


class CollapseModulePaths(metaclass=ABCMeta):
    """
    Replace private module paths with their public prefix so that object references
    can be matched by *intersphinx*.
    """

    # matches a full name of an object, including the preceding module path with at
    # least one private submodule (starting with a "_") directly preceding the item
    # name
    __RE_PRIVATE_MODULE_AND_ITEM = re.compile(
        r"\b(?# we start with a word break so we match full words)"
        r"(?# public module path)(\w+(?:\.\w+)*?)"
        r"(?# private module path)((?:\._\w+)+)"
        r"\."
        r"(?# item name)(\w+(?![.\w]))"
    )

    def __init__(
        self,
        collapsible_submodules: Mapping[str, str],
        collapse_private_modules: bool = True,
    ) -> None:
        """
        :param collapsible_submodules: mapping from module paths to their public
            prefix, e.g., ``{"pandas.core.frame": "pandas"}``
        :param collapse_private_modules: if ``True``, collapse module sub-paths
            consisting of one or more protected modules (i.e. the module name starts
            with an underscore)
        """
        super().__init__()
        self._classes_visited: set[type] = set()

        col = [
            self._make_substitution_pattern(old.replace(".", r"\."), new)
            for old, new in collapsible_submodules.items()
        ]

        self._intersphinx_collapsible_prefixes: list[tuple[Pattern[str], str]] = col
        self._collapse_private_modules = collapse_private_modules

    @abstractmethod
    def _make_substitution_pattern(
        self, old: str, new: str
    ) -> tuple[Pattern[str], str]:
        # create the regex substitution rule given a raw match and replacement patterns
        pass

    def collapse_module_paths(self, line: str) -> str:
        """
        In the given line, replace all module paths with their collapsed version.

        :param line: the line in which to collapse module paths
        :return: the resulting line with collapsed module paths
        """
        if self._collapse_private_modules:
            line = self._collapse_private_module_paths(line)

        for expanded, collapsed in self._intersphinx_collapsible_prefixes:
            line = expanded.sub(collapsed, line)

        return line

    @staticmethod
    def _collapse_private_module_paths(line: str) -> str:
        for (
            # e.g., "pytools.expression"
            public_module_path,
            # e.g., "._expression"
            private_module_path,
            # e.g., "Expression"
            item_name,
        ) in CollapseModulePaths.__RE_PRIVATE_MODULE_AND_ITEM.findall(line):
            module_path = public_module_path + private_module_path
            collapsed_path = public_module_path
            try:
                module = importlib.import_module(name=module_path)
                item = vars(module)[item_name]
                collapsed_path = item.__publicmodule__
            except KeyError:
                pass
            except AttributeError:
                pass
            except ModuleNotFoundError:
                pass

            line = line.replace(
                f"{module_path}.{item_name}", f"{collapsed_path}.{item_name}"
            )

        return line


@inheritdoc(match="""[see superclass]""")
class CollapseModulePathsInDocstring(CollapseModulePaths, AutodocProcessDocstring):
    """
    Replace private module paths in docstrings with their public prefix so that object
    references can be matched by *intersphinx*.
    """

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: list[str],
    ) -> None:
        """[see superclass]"""

        for i, line in enumerate(lines):
            lines[i] = self.collapse_module_paths(line)

    def _make_substitution_pattern(
        self, old: str, new: str
    ) -> tuple[Pattern[str], str]:
        return re.compile(f"(`~?){old}"), f"\\1{new}"


@inheritdoc(match="""[see superclass]""")
class CollapseModulePathsInSignature(CollapseModulePaths, AutodocProcessSignature):
    """
    Replace private module paths in signatures with their public prefix so that object
    references can be matched by *intersphinx*.
    """

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: str | None,
        return_annotation: str | None,
    ) -> tuple[str | None, str | None] | None:
        """[see superclass]"""
        if signature or return_annotation:
            return (
                self.collapse_module_paths(signature) if signature else None,
                (
                    self.collapse_module_paths(return_annotation)
                    if return_annotation
                    else None
                ),
            )

        return None

    def _make_substitution_pattern(
        self, old: str, new: str
    ) -> tuple[Pattern[str], str]:
        return re.compile(old), new


@inheritdoc(match="""[see superclass]""")
class CollapseModulePathsInXRef(ObjectDescriptionTransform, CollapseModulePaths):
    # noinspection GrazieInspection
    """
    Replace private module paths in documentation cross-references with their public
    prefix so that object references can be matched by *intersphinx*, and module
    paths correspond to what users are expected to use in their code.
    """

    # noinspection SpellCheckingInspection
    def process(
        self, app: Sphinx, domain: str, objtype: str, contentnode: Element
    ) -> None:
        """[see superclass]"""
        if domain == "py" and objtype == "class":
            self._process_children(contentnode)

    def _process_children(self, parent_node: Element) -> None:
        self._process_child(parent_node)
        try:
            children: Iterable[Element] = parent_node.children
        except AttributeError:
            # parent node is not an Element instance
            return
        for child_node in children:
            self._process_children(child_node)

    def _process_child(self, content_node: Element) -> None:
        if type(content_node).__name__ == "pending_xref" and tuple(
            type(c).__name__ for c in content_node.children
        ) == ("Text",):
            text_node: Text = cast(Text, content_node.children[0])
            text = text_node.astext()
            text_collapsed: str = self.collapse_module_paths(text)
            if text_collapsed != text:
                text_collapsed = text_collapsed.replace(
                    f'{content_node.attributes["py:module"]}.', ""
                )
                content_node.replace(
                    old=text_node,
                    new=type(text_node)(
                        data=text_collapsed, rawsource=text_node.rawsource
                    ),
                )

    def _make_substitution_pattern(
        self, old: str, new: str
    ) -> tuple[Pattern[str], str]:
        return re.compile(old), new


@inheritdoc(match="""[see superclass]""")
class SkipIndirectImports(AutodocSkipMember, metaclass=SingletonABCMeta):
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
    ) -> bool | None:
        """[see superclass]"""
        if not skip and what == "module" and name.startswith("_"):
            log.info(f"skipping: {what}: {name}")
            return False

        return None


@inheritdoc(match="""[see superclass]""")
class Replace3rdPartyDoc(AutodocProcessDocstring, metaclass=SingletonABCMeta):
    """
    Replace 3rd party docstrings with a reference to the 3rd party documentation.

    This is necessary for methods and attributes inherited from 3rd party packages,
    as these might use an incompatible format for docstrings.
    """

    __RE_ROOT_PACKAGE = re.compile(r"\w+(?=\.)")

    __RST_DIRECTIVE = {
        "module": "mod",
        "class": "class",
        "exception": "exception",
        "function": "func",
        "method": "meth",
        "attribute": "attr",
        "property": "attr",
    }

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: list[str],
    ) -> None:
        """[see superclass]"""

        if what == "attribute":
            # we cannot determine docstrings for attributes, as the object represents
            # the value of the attribute, and not the attribute itself
            mod_obj_attr = name.rsplit(".", 2)
            if len(mod_obj_attr) == 3:
                mod_name, obj_name, _ = mod_obj_attr
                obj = getattr(importlib.import_module(mod_name), obj_name)
            else:
                log.debug(f"could not determine module for {name}")
                return

        elif what == "property":
            obj = cast(property, obj).fget

        try:
            # if the object has an __objclass__ attribute, use that to determine the
            # module
            obj_module = getattr(obj, "__objclass__", obj).__module__
        except AttributeError:
            log.debug(f"could not determine module for {name}")
            return

        name_root_package = self.__root_package(name)
        obj_root_package = self.__root_package(obj_module) if obj_module else None

        if name_root_package != obj_root_package:
            # replace 3rd party docstring with cross-reference

            directive = Replace3rdPartyDoc.__RST_DIRECTIVE.get(what, what)

            if not isinstance(
                obj,
                (
                    FunctionType,
                    MethodType,
                    method_descriptor,
                    wrapper_descriptor,
                    internal_function_or_method,
                ),
            ):
                log.warning(f"{obj!r}:{type(obj)} is not a function or method")
                return

            if not obj_module or obj_module == "builtins":
                full_name = obj.__qualname__
            else:
                full_name = f"{public_module_prefix(obj_module)}.{obj.__qualname__}"

            del lines[:]
            lines.append(f"See :{directive}:`{full_name}`")

    @staticmethod
    def __root_package(name: str) -> str:
        root_package_match = Replace3rdPartyDoc.__RE_ROOT_PACKAGE.match(name)
        return root_package_match[0] if root_package_match else ""


#
# auxiliary functions
#


def _get_bases(subclass: type, include_subclass: bool) -> Generator[type, None, None]:
    # get the names of the immediate base classes of arg _subclass

    visited_classes: set[type] = set()

    def _inner(_subclass: type, _include_subclass: bool) -> Generator[type, None, None]:
        # ensure we have the non-generic origin class
        _subclass = typing_inspect.get_origin(_subclass) or _subclass

        if _subclass in visited_classes:
            return
        visited_classes.add(_subclass)

        # get the base classes; try generic bases first then fall back to regular
        # bases
        base_classes: tuple[type, ...] = (
            _get_generic_bases(_subclass) or _subclass.__bases__
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
            elif _class_name(base).startswith("_"):
                yield from _inner(base, _include_subclass=False)

            # all other classes will be listed as bases
            else:
                yield base

    return _inner(subclass, _include_subclass=include_subclass)


def _get_minimal_bases(class_: type) -> list[type]:
    bases_with_origin = [
        (base, typing_inspect.get_origin(base) or base)
        for base in set(_get_bases(class_, include_subclass=False))
    ]
    return [
        base
        for base, origin in bases_with_origin
        if not any(
            origin is not other and issubclass(other, origin)
            for _, other in bases_with_origin
        )
    ]


def _class_name(cls: Any) -> str:
    return cast(str, _class_attr(cls=cls, attr=["__qualname__", "__name__", "_name"]))


def _class_attr(cls: Any, attr: list[str]) -> Any:
    def _get_attr(_cls: type) -> Any:
        # we try to get the class attribute
        for attr_name in attr:
            attr_value = getattr(_cls, attr_name, None)
            if attr_value is not None:
                return attr_value

        # if the attribute is not defined, this class is likely to have generic
        # arguments, so we re-try recursively with the origin (unless the origin
        # is the class itself to avoid infinite recursion)
        cls_origin = typing_inspect.get_origin(_cls)
        if cls_origin is not None and cls_origin != _cls:
            return _get_attr(cls_origin)
        else:
            # as a last resort, we create the default value
            raise AttributeError(
                f"none of the attributes not found in class {cls}: {', '.join(attr)}"
            )

    return _get_attr(_cls=typing.get_origin(cls) or cls)


class _TypeVarBindings:
    current_class: type[Any]
    _bindings: dict[
        type[Any],
        dict[
            TypeVar,
            type[Any] | TypeVar,
        ],
    ]

    def __init__(self, current_class: type[Any]) -> None:
        super().__init__()

        self.current_class = current_class
        self._bindings = self._get_parameter_bindings(
            cls=current_class, subclass_bindings={}
        )

    def resolve_parameter(
        self, defining_class: type[Any], parameter: TypeVar
    ) -> type[Any] | TypeVar:
        """
        Resolve a type parameter, substituting it with an actual type if the parameter
        is bound to a type argument in the context of the current class;
        otherwise return the parameter unchanged.

        :param defining_class: the class that introduced the type parameter; this is
            the current class itself, or a base class of the current class
        :param parameter: the type variable
        :return: the resolved parameter if bound to a type argument; else the original
            parameter as a type variable
        """
        return self._bindings.get(defining_class, {}).get(parameter, parameter)

    def _get_parameter_bindings(
        self,
        cls: type[Any],
        subclass_bindings: dict[TypeVar, type[Any] | TypeVar],
    ) -> dict[type[Any], dict[TypeVar, type[Any] | TypeVar]]:
        # get type variable bindings for all generic types defined in the class
        # hierarchy of the given parent class, applying the given bindings derived from
        # child classes

        # if arg cls has generic type parameters, it will have a corresponding
        cls_origin: type[Any] | None = None
        if typing_inspect.is_generic_type(cls):
            cls_origin = typing_inspect.get_origin(cls)

        class_bindings: dict[TypeVar, type[Any] | TypeVar]
        if cls_origin:
            class_bindings = {
                param: subclass_bindings.get(arg, arg) if subclass_bindings else arg
                for param, arg in zip(
                    typing_inspect.get_parameters(cls_origin),
                    typing_inspect.get_args(cls),
                )
            }
            cls = cls_origin
        else:
            # this class has no generic parameters of itself, so we adopt the existing
            # parameter bindings from the subclass(es)
            class_bindings = subclass_bindings

        superclass_bindings = {
            superclass: bindings
            for generic_superclass in _get_generic_bases(cls)
            for superclass, bindings in (
                self._get_parameter_bindings(
                    cls=generic_superclass, subclass_bindings=class_bindings
                ).items()
            )
            if bindings
        }

        if cls_origin:
            # we have generic type parameters in this class, so we remember the
            # associated bindings
            return {cls_origin: class_bindings, **superclass_bindings}
        else:
            # we have no generic type parameters in this class, so we return the
            # parameter bindings of the superclasses
            return superclass_bindings


@inheritdoc(match="""[see superclass]""")
class ResolveTypeVariables(AutodocBeforeProcessSignature, metaclass=SingletonABCMeta):
    """
    Resolve type variables that can be inferred through generic class parameters or
    ``self``/``cls`` special arguments.

    For example, the Sphinx documentation for the inherited method ``B.f`` in the
    following example will be rendered with the signature ``(int) -> int``:

    .. code-block:: python

        T = TypeVar("T")

        class A(Generic[T]):
            def f(x: T) -> T:
                return x

        class B(A[int]):
            pass

    """

    original_signatures: dict[Any, dict[str, type[Any] | TypeVar]]

    _current_class: type[Any] | None
    _current_class_bindings: _TypeVarBindings | None
    _track_current_class: TrackCurrentClass

    def __init__(self) -> None:
        super().__init__()

        self.original_signatures = {}
        self._current_class = None
        self._current_class_bindings = None
        self._track_current_class = TrackCurrentClass()

    def connect(self, app: Sphinx, priority: int | None = None) -> int:
        """[see superclass]"""

        if TrackCurrentClass().app is not app:
            raise RuntimeError(
                f"connect {TrackCurrentClass.__name__}() to the same app "
                f"before connecting {ResolveTypeVariables.__name__}()"
            )

        return super().connect(app, priority)

    def _resolve_function_signature(
        self, bindings: _TypeVarBindings, func: FunctionType
    ) -> None:
        # get the class in which the method has been defined
        defining_class_opt: type[Any] | None = self._get_defining_class(func)
        if defining_class_opt is None:
            # missing or unknown defining class: nothing to resolve in the signature
            return
        defining_class: type = defining_class_opt

        # get the original signature and convert it to a list of (name, type) tuples
        signature_original_items = list(self._get_original_signature(func).items())

        def _get_self_or_cls_type_substitution() -> (
            tuple[TypeVar, type[Any]] | tuple[None, None]
        ):
            if signature_original_items:
                method_type = self._get_method_type(defining_class, func)

                if method_type is METHOD_TYPE_DYNAMIC:
                    # special case: we substitute type vars bound to the class
                    # when assigned to the 'self' or 'cls' parameters of methods
                    _, arg_0_type = signature_original_items[0]
                    if typing_inspect.is_typevar(arg_0_type):
                        return cast(TypeVar, arg_0_type), bindings.current_class

                elif method_type is METHOD_TYPE_CLASS:
                    # special case: we substitute type vars bound to the class
                    # when assigned to the 'self' or 'cls' parameters of methods
                    _, arg_0_type = signature_original_items[0]
                    if (
                        typing_inspect.is_generic_type(arg_0_type)
                        and typing_inspect.get_origin(arg_0_type) is type
                    ):
                        arg_0_type_args = typing_inspect.get_args(arg_0_type)
                        if len(arg_0_type_args) == 1 and typing_inspect.is_typevar(
                            arg_0_type_args[0]
                        ):
                            return arg_0_type_args[0], bindings.current_class

            return None, None

        arg_0_type_var: TypeVar | None
        arg_0_substitute: type[Any] | None

        arg_0_type_var, arg_0_substitute = _get_self_or_cls_type_substitution()

        def _substitute_type_vars_in_type_expression(
            type_expression: type[Any] | TypeVar,
        ) -> type[Any] | TypeVar:
            # recursively substitute type vars with their resolutions
            if isinstance(type_expression, TypeVar):
                if type_expression == arg_0_type_var:
                    # special case: substitute a type variable introduced by the
                    # initial self/cls argument of a dynamic or class method
                    assert arg_0_substitute is not None
                    return arg_0_substitute
                else:
                    # resolve type variables defined by Generic[] in the
                    # class hierarchy
                    return bindings.resolve_parameter(defining_class, type_expression)
            else:
                # dynamically resolve type variables inside nested type expressions
                return _substitute_generic_type_arguments(
                    type_expression=type_expression,
                    fn_substitute_type_vars=_substitute_type_vars_in_type_expression,
                )

        # get the actual signature object that we will modify
        signature = func.__annotations__
        if not signature:
            return

        for name, tp in signature_original_items:
            signature[name] = _substitute_type_vars_in_type_expression(tp)

    def _resolve_attribute_signatures(self, cls: type[Any]) -> None:
        assert self._current_class_bindings is not None
        bindings: _TypeVarBindings = self._current_class_bindings

        def _substitute_type_vars_in_type_expression(
            type_expression: type[Any] | TypeVar,
        ) -> type[Any] | TypeVar:
            # recursively substitute type vars with their resolutions
            if isinstance(type_expression, TypeVar):
                # resolve type variables defined by Generic[] in the
                # class hierarchy
                return bindings.resolve_parameter(cls, type_expression)
            else:
                return _substitute_generic_type_arguments(
                    type_expression=type_expression,
                    fn_substitute_type_vars=_substitute_type_vars_in_type_expression,
                )

        annotations = getattr(cls, "__annotations__", None)
        if annotations:
            cls.__annotations__ = {
                attr: _substitute_type_vars_in_type_expression(annotation)
                for attr, annotation in annotations.items()
            }

    @staticmethod
    def _get_defining_class(method: FunctionType) -> type[Any] | None:
        # get the class that defined the callable

        if "." not in method.__qualname__:
            # this is a function, not a method
            return None

        method_container: str
        if method.__qualname__.endswith(f".{method.__name__}"):
            method_container = method.__qualname__[: -len(method.__name__) - 1]
        else:
            method_container = method.__qualname__[: method.__qualname__.rfind(".")]

        try:
            return cast(
                type[Any],
                eval(
                    method_container,
                    importlib.import_module(method.__module__).__dict__,
                ),
            )
        except NameError:
            # we could not find the container of the given method in the method's global
            # namespace - this is likely an inherited method where the parent class
            # sits in a different module
            log.debug(
                f"failed to find container '{method.__module__}.{method_container}' "
                f"of method '{method.__name__}'"
            )
            return None

    @staticmethod
    def _get_method_type(defining_class: type[Any], func: FunctionType) -> int:
        # do we have a static or class method?
        try:
            raw_func = getattr_static(defining_class, func.__name__)
            if isinstance(raw_func, staticmethod):
                return METHOD_TYPE_STATIC
            elif isinstance(raw_func, classmethod):
                return METHOD_TYPE_CLASS
        except AttributeError:
            # this should not happen, but we try to handle this gracefully
            log.warning(
                f"failed to look up method {func.__name__!r} "
                f"in class {defining_class.__name__}"
            )
        return METHOD_TYPE_DYNAMIC

    def _get_original_signature(
        self, func: FunctionType
    ) -> dict[str, type[Any] | TypeVar]:
        # get the original signature as defined in the code
        signature_original: dict[str, type[Any] | TypeVar]
        try:
            signature_original = self.original_signatures[func]
        except KeyError:
            signature_original = get_type_hints(func)
            self.original_signatures[func] = signature_original
        return signature_original

    def process(self, app: Sphinx, obj: Any, bound_method: bool) -> None:
        """[see superclass]"""

        self._update_current_class(self._track_current_class.current_class)

        if isinstance(obj, FunctionType):
            # instance method definitions are unbound, so we need to determine
            # the class we are currently in from context

            bindings: _TypeVarBindings | None
            if obj.__name__ == obj.__qualname__:
                # this is a function, not a method
                return

            defining_class = self._get_defining_class(obj)
            assert (
                defining_class is not None
            ), f"function {obj.__qualname__} has a defining class"

            if obj.__name__ in ["__init__", "__init_subclass__", "__new__"] or (
                obj.__name__ == "__call__" and issubclass(defining_class, type)
            ):
                # special case of class initializer, this usually means that we are
                # starting to document a new class, or refer to a special method
                # of a metaclass
                bindings = self._update_current_class(defining_class)
            else:
                bindings = self._current_class_bindings

            assert (
                bindings is not None
            ), f"bindings are in place for function {obj.__qualname__}"
            assert issubclass(bindings.current_class, defining_class), (
                f"current class {bindings.current_class.__name__} "
                f"is a subclass of the class of unbound method {obj.__qualname__}, "
                f"class={defining_class}"
            )

            self._resolve_function_signature(bindings=bindings, func=obj)

        elif isinstance(obj, MethodType):
            # class method definitions are bound, so we can infer the current class
            cls = obj.__self__
            assert isinstance(cls, type), "methods are class methods"

            bindings = self._current_class_bindings
            assert (
                bindings is not None
            ), "bindings expected to be in place when processing a bound method"
            assert (
                bindings.current_class is cls
            ), "bindings expected to be for the correct class"

            self._resolve_function_signature(
                bindings=bindings, func=cast(FunctionType, obj.__func__)
            )

    def _update_current_class(self, cls: type[Any] | None) -> _TypeVarBindings | None:
        if cls is None:
            return None

        bindings: _TypeVarBindings | None = self._current_class_bindings

        if bindings is None or bindings.current_class is not cls:
            # we're visiting a new class
            log.debug(f"visiting new class {cls.__name__}")

            # create a TypeVar bindings object for this class
            bindings = self._current_class_bindings = _TypeVarBindings(cls)

            # and resolve type variables in type annotations for class attributes
            self._resolve_attribute_signatures(cls=cls)

        return bindings


@inheritdoc(match="""[see superclass]""")
class TrackCurrentClass(AutodocProcessSignature, metaclass=SingletonABCMeta):
    """
    Keep track of the class currently being processed by autodoc.

    This is required to attribute unbound methods to the correct class, e.g.,
    in class :class:`.ResolveTypeVariables`.
    """

    #: The class currently being processed by autodoc.
    current_class: type[Any] | None

    def __init__(self) -> None:
        super().__init__()

        self.current_class = None

    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: str | None,
        return_annotation: str | None,
    ) -> tuple[str | None, str | None] | None:
        """[see superclass]"""

        if what == "class":
            cls = cast(type, obj)
            self.current_class = cls

        return None


@inheritdoc(match="""[see superclass]""")
class RenamePrivateArguments(AutodocBeforeProcessSignature, metaclass=SingletonABCMeta):
    """
    Rename private argument names to their original names given in the source code.

    For example, arg ``__x`` of method ``f`` in

    .. code-block:: python

        class A:
            def f(self, __x: int) -> None:
                ...

    will be renamed from its internal, private name ``_A__x`` back to ``__x``.
    """

    def process(self, app: Sphinx, obj: Any, bound_method: bool) -> None:
        """[see superclass]"""

        if not (bound_method or isinstance(obj, FunctionType)):
            return

        # get the name of the module or class that the function is a member of
        try:
            containers = obj.__qualname__.split(".")
        except AttributeError:
            return

        if len(containers) < 2:
            return

        private_prefix = f"_{containers[-2]}__"

        def get_public_name(name: str) -> str:
            if name.startswith(private_prefix):
                return name[len(private_prefix) - 2 :]
            else:
                return name

        # get the original signature
        try:
            annotations: dict[str, Any] = obj.__annotations__
        except AttributeError:
            annotations = {}

        annotations_original = list(annotations.items())
        for name, annotation in annotations_original:
            public_name = get_public_name(name)
            if public_name is not name:
                del annotations[name]
                annotations[public_name] = annotation

        try:
            code = obj.__code__
            arg_and_variable_names = code.co_varnames
            if any(name.startswith(private_prefix) for name in arg_and_variable_names):
                obj.__code__ = code.replace(
                    co_varnames=tuple(
                        get_public_name(name) for name in arg_and_variable_names
                    ),
                )
        except AttributeError:
            pass


@inheritdoc(match="""[see superclass]""")
class UpdateForwardReferences(AutodocProcessSignature, metaclass=SingletonABCMeta):
    """
    A Sphinx autodoc process signature that updates forward references in the
    docstring of a class.
    """

    @subsdoc(
        # match and delete the row that declares :return:
        # remember this is a multiline string, so we need to match the whole line
        pattern=r"\s*:return:.*",
        replacement="",
        using=AutodocProcessSignature.process,
    )
    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: str | None,
        return_annotation: str | None,
    ) -> None:
        """[see superclass]"""

        if what == "class":
            try:
                update_forward_references(cast(type, obj))
            except Exception as e:
                log.error(f"failed to update forward references for {name}: {e}")
                # print the traceback to the console
                import traceback

                traceback.print_exc()

                raise

        return None


#
# validate __all__
#

__tracker.validate()


def _substitute_generic_type_arguments(
    type_expression: type[Any] | TypeVar,
    fn_substitute_type_vars: typing.Callable[
        [type[Any] | TypeVar], type[Any] | TypeVar
    ],
) -> type[Any] | TypeVar:
    # dynamically resolve type variables inside nested type expressions
    type_args: tuple[list[type[Any] | TypeVar] | type[Any] | TypeVar, ...] = (
        typing_inspect.get_args(type_expression)
    )

    if type_args:

        if isinstance(type_expression, UnionType):
            type_expression = Union[type_args[0], type_args[1]]
        return _copy_generic_type_with_arguments(
            type_expression=type_expression,
            new_arguments=tuple(
                (
                    list(map(fn_substitute_type_vars, arg))
                    if isinstance(arg, list)
                    else fn_substitute_type_vars(arg)
                )
                for arg in type_args
            ),
        )
    else:
        return type_expression


def _copy_generic_type_with_arguments(
    type_expression: type[Any] | TypeVar,
    new_arguments: tuple[list[type[Any] | TypeVar] | type[Any] | TypeVar, ...],
) -> type[Any] | TypeVar:
    # create a copy of the given type expression, replacing its type arguments with
    # the given new arguments

    origin = typing_inspect.get_origin(type_expression)
    assert origin is not None

    try:
        copy_with: Callable[
            [
                tuple[
                    list[type[Any] | TypeVar] | type[Any] | TypeVar,
                    ...,
                ]
            ],
            type[Any] | TypeVar,
        ] = type_expression.copy_with  # type: ignore
    except AttributeError:
        # this is a generic type that does not support copying
        return cast(type[Any], origin[new_arguments])

    # unpack callable args, since copy_with() expects a flat tuple
    # (arg_1, arg_2, ..., arg_n, return)
    # instead of ([arg_1, arg_2, ..., arg_n], return)
    if (origin is collections.abc.Callable) and isinstance(new_arguments[0], list):
        new_arguments = (*new_arguments[0], *new_arguments[1:])

    return copy_with(new_arguments)


def _get_generic_bases(class_: type) -> tuple[type, ...]:
    """
    Bugfix version of :func:`typing_inspect.get_generic_bases`.

    Prevents getting the generic bases of the parent class if not defined for the given
    class.

    :param class_: class to get the generic bases for
    :return: the generic base classes of the given class
    """
    bases: tuple[type, ...] = typing_inspect.get_generic_bases(class_)
    if not isinstance(
        class_, GenericAlias
    ) and bases is typing_inspect.get_generic_bases(super(class_, class_)):
        return ()
    else:
        return bases
