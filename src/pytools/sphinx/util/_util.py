"""
Implementation of sphinx utility callbacks specific to building Gamma documentation.
"""
import collections.abc
import importlib
import itertools
import logging
import re
import sys
import typing
from abc import ABCMeta, abstractmethod
from inspect import getattr_static
from types import FunctionType, MethodType
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    Generator,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)

import typing_inspect

from ...api import AllTracker, get_generic_bases, inheritdoc, public_module_prefix
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

        children: List["Element"]
        attributes: Dict[str, Any]

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise TypeError("docutils package is not installed")

        def replace(self, old: "Element", new: "Element") -> None:
            ...

    # noinspection PyMissingOrEmptyDocstring,SpellCheckingInspection
    class _Text(_Element):

        rawsource: str

        # noinspection SpellCheckingInspection
        def astext(self) -> str:
            ...

    Sphinx = type("Sphinx", (object,), {})
    Element = _Element
    Text = _Text


#
# Constants
#

_PYTHON_3_9_OR_LATER = sys.version_info >= (3, 9)


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
    "Replace3rdPartyDoc",
    "ResolveTypeVariables",
    "SkipIndirectImports",
]

#
# Type aliases
#

method_descriptor = type(str.__dict__["startswith"])
wrapper_descriptor = type(str.__dict__["__add__"])


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
        self._visited: Dict[type, str] = {}

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
        lines: List[str],
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

        bases_lines: List[str] = [""]

        bases: List[type] = _get_minimal_bases(class_)
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

        self._insert_bases_lines(bases_lines, lines)

    @staticmethod
    def _insert_bases_lines(bases_lines: List[str], lines: List[str]) -> None:
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

    def _class_module(self, cls: Any) -> str:
        module_name: str = _class_attr(cls, attr=["__publicmodule__", "__module__"])

        # return the collapsed submodule if it exists,
        # else return the unchanged module name
        return self.collapsible_submodules.get(module_name, module_name)

    def _full_name(self, cls: Any) -> str:
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
        self._classes_visited: Set[type] = set()

        col = [
            self._make_substitution_pattern(old.replace(".", r"\."), new)
            for old, new in collapsible_submodules.items()
        ]

        self._intersphinx_collapsible_prefixes: List[Tuple[Pattern[str], str]] = col
        self._collapse_private_modules = collapse_private_modules

    @abstractmethod
    def _make_substitution_pattern(
        self, old: str, new: str
    ) -> Tuple[Pattern[str], str]:
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
        lines: List[str],
    ) -> None:
        """[see superclass]"""

        for i, line in enumerate(lines):
            lines[i] = self.collapse_module_paths(line)

    def _make_substitution_pattern(
        self, old: str, new: str
    ) -> Tuple[Pattern[str], str]:
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
        signature: Optional[str],
        return_annotation: Optional[str],
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
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
    ) -> Tuple[Pattern[str], str]:
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
    ) -> Tuple[Pattern[str], str]:
        return re.compile(old), new


@inheritdoc(match="""[see superclass]""")
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
        if not skip and what == "module" and name.startswith("_"):
            log.info(f"skipping: {what}: {name}")
            return False

        return None


@inheritdoc(match="""[see superclass]""")
class Replace3rdPartyDoc(AutodocProcessDocstring):
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
        lines: List[str],
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

            assert isinstance(
                obj, (FunctionType, MethodType, method_descriptor, wrapper_descriptor)
            ), f"{obj!r}:{type(obj)} is a function or method"

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

    visited_classes: Set[type] = set()

    def _inner(_subclass: type, _include_subclass: bool) -> Generator[type, None, None]:
        # ensure we have the non-generic origin class
        _subclass = typing_inspect.get_origin(_subclass) or _subclass

        if _subclass in visited_classes:
            return
        visited_classes.add(_subclass)

        # get the base classes; try generic bases first then fall back to regular
        # bases
        base_classes: Tuple[type, ...] = (
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
            elif _class_name(base).startswith("_"):
                yield from _inner(base, _include_subclass=False)

            # all other classes will be listed as bases
            else:
                yield base

    return _inner(subclass, _include_subclass=include_subclass)


def _get_minimal_bases(class_: type) -> List[type]:
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


def _class_attr(cls: Any, attr: List[str]) -> Any:
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

    return _get_attr(_cls=cls)


class _TypeVarBindings:
    def __init__(self, current_class: type) -> None:
        self.current_class = current_class
        self._bindings = self._get_parameter_bindings(
            cls=current_class, subclass_bindings={}
        )

    def resolve_parameter(
        self, defining_class: Type[Any], parameter: TypeVar
    ) -> Union[Type[Any], TypeVar]:
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
        cls: Type[Any],
        subclass_bindings: Dict[TypeVar, Union[Type[Any], TypeVar]],
    ) -> Dict[Type[Any], Dict[TypeVar, Union[Type[Any], TypeVar]]]:
        # get type variable bindings for all generic types defined in the class
        # hierarchy of the given parent class, applying the given bindings derived from
        # child classes

        # if arg cls has generic type parameters, it will have a corresponding
        cls_origin: Optional[Type[Any]] = None
        if typing_inspect.is_generic_type(cls):
            cls_origin = typing_inspect.get_origin(cls)

        class_bindings: Dict[TypeVar, Union[Type[Any], TypeVar]]
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
            for generic_superclass in get_generic_bases(cls)
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
class ResolveTypeVariables(AutodocBeforeProcessSignature):
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

    original_signatures: Dict[Any, Dict[str, Union[Type[Any], TypeVar]]]

    _current_class_bindings: Optional[_TypeVarBindings]

    def __init__(self) -> None:
        self.original_signatures = {}
        self._current_class_bindings = None

    def _resolve_function_signature(
        self, bindings: _TypeVarBindings, func: FunctionType
    ) -> None:
        # get the class in which the method has been defined
        defining_class_opt: Optional[Type[Any]] = self._get_defining_class(func)
        if defining_class_opt is None:
            # missing or unknown defining class: nothing to resolve in the signature
            return
        defining_class: type = defining_class_opt

        # get the original signature and convert it to a list of (name, type) tuples
        signature_original_items = list(self._get_original_signature(func).items())

        def _get_self_or_cls_type_substitution() -> Union[
            Tuple[TypeVar, Type[Any]], Tuple[None, None]
        ]:

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

        arg_0_type_var: Optional[TypeVar]
        arg_0_substitute: Optional[Type[Any]]

        arg_0_type_var, arg_0_substitute = _get_self_or_cls_type_substitution()

        def _substitute_type_vars_in_type_expression(
            type_expression: Union[Type[Any], TypeVar]
        ) -> Union[Type[Any], TypeVar]:
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

    def _resolve_attribute_signatures(self, cls: Type[Any]) -> None:
        assert self._current_class_bindings is not None
        bindings: _TypeVarBindings = self._current_class_bindings

        def _substitute_type_vars_in_type_expression(
            type_expression: Union[Type[Any], TypeVar]
        ) -> Union[Type[Any], TypeVar]:
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
    def _get_defining_class(method: FunctionType) -> Optional[Type[Any]]:
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
                Type[Any],
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
    def _get_method_type(defining_class: Type[Any], func: FunctionType) -> int:
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
    ) -> Dict[str, Union[Type[Any], TypeVar]]:
        # get the original signature as defined in the code
        signature_original: Dict[str, Union[Type[Any], TypeVar]]
        try:
            signature_original = self.original_signatures[func]
        except KeyError:
            signature_original = get_type_hints(func)
            self.original_signatures[func] = signature_original
        return signature_original

    def process(self, app: Sphinx, obj: Any, bound_method: bool) -> None:
        """[see superclass]"""

        if isinstance(obj, type):
            # we are starting to process a new class; remember it, so we can
            # attribute unbound methods to it
            self._update_current_class(obj)

        elif isinstance(obj, FunctionType):
            bindings = self._update_current_class(self._get_defining_class(obj))

            # instance method definitions are unbound, so we need to remember
            # the class we are currently in
            if bindings is not None:
                self._resolve_function_signature(bindings=bindings, func=obj)

        elif isinstance(obj, MethodType):
            # class method definitions are bound, so we can infer the current class
            cls = obj.__self__
            assert isinstance(cls, type), "methods are class methods"

            current_class: Optional[_TypeVarBindings] = self._update_current_class(cls)
            assert current_class is not None
            # noinspection PyTypeChecker
            self._resolve_function_signature(bindings=current_class, func=obj.__func__)

    def _update_current_class(
        self, cls: Optional[Type[Any]]
    ) -> Optional[_TypeVarBindings]:
        if cls is None:
            return None

        bindings: Optional[_TypeVarBindings] = self._current_class_bindings
        assert isinstance(cls, type), f"{cls} is a class"
        if bindings is None or not issubclass(bindings.current_class, cls):
            # we're visiting the class for the first time

            # create a TypeVar bindings object for this class
            bindings = self._current_class_bindings = _TypeVarBindings(cls)

            # and resolve type variables in type annotations for class attributes
            self._resolve_attribute_signatures(cls=cls)

        return bindings


#
# validate __all__
#

__tracker.validate()


def _substitute_generic_type_arguments(
    type_expression: Union[Type[Any], TypeVar],
    fn_substitute_type_vars: typing.Callable[
        [Union[Type[Any], TypeVar]], Union[Type[Any], TypeVar]
    ],
) -> Union[Type[Any], TypeVar]:
    # dynamically resolve type variables inside nested type expressions
    type_args: Tuple[
        Union[List[Union[Type[Any], TypeVar]], Union[Type[Any], TypeVar]], ...
    ] = typing_inspect.get_args(type_expression)

    if type_args:
        return _copy_generic_type_with_arguments(
            type_expression=type_expression,
            new_arguments=tuple(
                list(map(fn_substitute_type_vars, arg))
                if isinstance(arg, list)
                else fn_substitute_type_vars(arg)
                for arg in type_args
            ),
        )
    else:
        return type_expression


def _copy_generic_type_with_arguments(
    type_expression: Union[Type[Any], TypeVar],
    new_arguments: Tuple[
        Union[List[Union[Type[Any], TypeVar]], Union[Type[Any], TypeVar]], ...
    ],
) -> Union[Type[Any], TypeVar]:
    # create a copy of the given type expression, replacing its type arguments with
    # the given new arguments

    origin = typing_inspect.get_origin(type_expression)
    assert origin is not None

    try:
        copy_with: Callable[
            [
                Tuple[
                    Union[List[Union[Type[Any], TypeVar]], Union[Type[Any], TypeVar]],
                    ...,
                ]
            ],
            Union[Type[Any], TypeVar],
        ] = type_expression.copy_with  # type: ignore
    except AttributeError:
        # this is a generic type that does not support copying
        return cast(Type[Any], origin[new_arguments])

    # unpack callable args, since copy_with() expects a flat tuple
    # (arg_1, arg_2, ..., arg_n, return)
    # instead of ([arg_1, arg_2, ..., arg_n], return)
    if (origin is collections.abc.Callable) and isinstance(new_arguments[0], list):
        new_arguments = (*new_arguments[0], *new_arguments[1:])

    return copy_with(new_arguments)
