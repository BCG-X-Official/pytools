"""
Implementation of sphinx utility callbacks specific to building Gamma documentation.
"""
import importlib
import itertools
import logging
import re
from abc import ABCMeta, abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Pattern,
    Set,
    Tuple,
    TypeVar,
    cast,
)

import typing_inspect

from ...api import AllTracker, get_generic_bases, inheritdoc, public_module_prefix
from .. import (
    AutodocProcessDocstring,
    AutodocProcessSignature,
    AutodocSkipMember,
    ObjectDescriptionTransform,
)

try:
    # ForwardRef was introduced in Python 3.7, so be prepared for an ImportError
    # noinspection PyUnresolvedReferences
    from typing import ForwardRef
except ImportError:
    # in Python 3.6, ForwardRef is called _ForwardRef
    # noinspection PyProtectedMember,PyUnresolvedReferences
    from typing import _ForwardRef as ForwardRef


try:
    # import sphinx classes if available ...
    from docutils.nodes import Text
    from sphinx.application import Sphinx
    from sphinx.util.docutils import Node
except ImportError:
    # ... otherwise mock them up
    Sphinx = Any
    Node = Any
    Text = Any

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
    "SkipIndirectImports",
]


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

    F_BASES = ":bases:"  #: Field directive for base classes.
    F_GENERICS = ":generic types:"  #: Field directive for generic types.
    F_METACLASSES = ":metaclasses:"  #: Field directive for metaclasses.

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
                        n == 0 or not lines[n - 1].strip()
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
                # we try to get the class attribute
                return getattr(_cls, attr)
            except AttributeError:
                # if the attribute is not defined, this class is likely to have generic
                # arguments, so we re-try recursively with the origin (unless the origin
                # is the class itself to avoid infinite recursion)
                cls_origin = typing_inspect.get_origin(cls)
                if cls_origin != _cls:
                    return _get_attr(_cls=cls_origin)
                else:
                    # as a last resort, we create the default value
                    return default()

        return _get_attr(_cls=cls)

    def _class_module(self, cls: type) -> str:
        module_name = AddInheritance._class_attr(
            cls=cls,
            attr="__publicmodule__",
            default=lambda: AddInheritance._class_attr(
                cls=cls, attr="__module__", default=lambda: ""
            ),
        )

        # return the collapsed submodule if it exists,
        # else return the unchanged module name
        return self.collapsible_submodules.get(module_name, module_name)

    @staticmethod
    def _class_name(cls: type) -> str:
        return AddInheritance._class_attr(
            cls=cls, attr="__qualname__", default=lambda: str(cls)
        )

    def _full_name(self, cls: type) -> str:
        # get the full name of the class, including the module prefix
        return f"{self._class_module(cls=cls)}.{self._class_name(cls=cls)}"

    def _class_name_with_generics(self, cls: Any) -> str:
        def _class_tag(_name: Any) -> str:
            return f":class:`{str(_name)}`"

        if isinstance(cls, TypeVar):
            return _class_tag(cls)

        if isinstance(cls, ForwardRef):
            if cls.__forward_evaluated__:
                cls = cls.__forward_value__
            else:
                return _class_tag(f".{cls.__forward_arg__}")

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

        self._intersphinx_collapsible_prefixes: List[Tuple[Pattern, str]] = col
        self._collapse_private_modules = collapse_private_modules

    @abstractmethod
    def _make_substitution_pattern(self, old: str, new: str) -> Tuple[Pattern, str]:
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

        if self._collapse_private_modules:
            line = self._collapse_private_module_paths(line)

        for expanded, collapsed in self._intersphinx_collapsible_prefixes:
            line = expanded.sub(collapsed, line)

        return line

    @staticmethod
    def _collapse_private_module_paths(line: str) -> str:
        for (
            public_module_path,  # e.g., "pytools.expression"
            private_module_path,  # e.g., "._expression"
            item_name,  # e.g., "Expression"
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

    def _make_substitution_pattern(self, old: str, new: str) -> Tuple[Pattern, str]:
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
                self.collapse_module_paths(signature),
                self.collapse_module_paths(return_annotation),
            )

    def _make_substitution_pattern(self, old: str, new: str) -> Tuple[Pattern, str]:
        return re.compile(old), new


@inheritdoc(match="""[see superclass]""")
class CollapseModulePathsInXRef(ObjectDescriptionTransform, CollapseModulePaths):
    """
    Replace private module paths in documentation cross-references with their public
    prefix so that object references can be matched by *intersphinx*, and module
    paths correspond to what users are expected to use in their code.
    """

    # noinspection SpellCheckingInspection
    def process(
        self, app: Sphinx, domain: str, objtype: str, contentnode: Node
    ) -> None:
        """[see superclass]"""
        if domain == "py" and objtype == "class":
            self._process_children(contentnode)

    def _process_children(self, parent_node: Node):
        self._process_child(parent_node)
        try:
            children: Iterable[Node] = parent_node.children
        except AttributeError:
            # parent node is not an Element instance
            return
        for child_node in children:
            self._process_children(child_node)

    def _process_child(self, content_node: Node):
        if type(content_node).__name__ == "pending_xref" and tuple(
            type(c).__name__ for c in content_node.children
        ) == ("Text",):
            text_node: Text = content_node.children[0]
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

    def _make_substitution_pattern(self, old: str, new: str) -> Tuple[Pattern, str]:
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
        if not skip:
            if what == "module" and name.startswith("_"):
                log.info(f"skipping: {what}: {name}")
                return False


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
# validate __all__
#

__tracker.validate()
