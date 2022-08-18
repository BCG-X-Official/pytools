"""
Core implementation of :mod:`pytools.api`.
"""

import logging
import re
from types import FunctionType
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
    get_type_hints,
)

log = logging.getLogger(__name__)

__all__ = [
    "AllTracker",
    "public_module_prefix",
    "update_forward_references",
]


#
# Type variables
#

T = TypeVar("T")
T_Collection = TypeVar("T_Collection", bound=Collection[Any])
T_Callable = TypeVar("T_Callable", bound=Callable[..., Any])
T_Iterable = TypeVar("T_Iterable", bound=Iterable[Any])
T_Type = TypeVar("T_Type", bound=type)


#
# The AllTracker, used to check that __all__ includes all publicly defined symbols
#


class AllTracker:
    """
    Track global, public items defined in a module and validate that all eligible items
    have been included in the ``__all__`` variable.

    Items will be tracked if:

    - their name does not start with an underscore character
    - they are defined after the :class:`.AllTracker` instance has been created

    The underlying idea (and widely used pattern in GAMMA packages) is to define all
    items in one or more private submodules, export all public items using the
    ``__all__`` keyword, and import them into a public package one level up
    (usually the package's ``__init__.py``).

    This ensures a clean namespace in the public package, uncluttered by any imports
    used in the private module.

    The tracker also performs additional checks to validate the eligibility of
    definitions for being exported:

    - constant definitions should not be exported, as this will pose difficulties
      with Sphinx documentation and - from an API design perspective - provides less
      context than defining constants inside classes
    - definitions exported from other modules should not be re-exported by the importing
      module

    These validation checks can be overridden if required in special cases.
    """

    #: if ``True``, automatically replace all forward
    #: type references in function annotations with the referenced classes;
    #: see :func:`.update_forward_references`
    update_forward_references: bool

    #: if ``True``, allow exporting public global constants in ``__all__``;
    #: these typically have no ``__module__`` or ``__doc__`` attributes and will
    #: not be properly rendered in generated documentation
    allow_global_constants: bool

    #: if ``True``, allow exporting definitions in ``__all__`` even if they have been
    #: imported from another module
    allow_imported_definitions: bool

    # noinspection PyShadowingNames
    def __init__(
        self,
        globals_: Dict[str, Any],
        *,
        public_module: Optional[str] = None,
        update_forward_references: bool = True,
        allow_global_constants: bool = False,
        allow_imported_definitions: bool = False,
    ) -> None:
        """
        :param globals_: the dictionary of global variables obtained by calling
            :meth:`.globals` in the current module scope
        :param public_module: full name of the public module that will export the items
            managed by this tracker
        :param update_forward_references: if ``True``, automatically replace all forward
            type references in function annotations with the referenced classes; see
            :func:`.update_forward_references`
            (default: ``True``)
        :param allow_global_constants: if ``True``, allow exporting public global
            constants in ``__all__``;
            these typically have no ``__module__`` or ``__doc__`` attributes and will
            not be properly rendered in generated documentation (default: ``False``)
        :param allow_imported_definitions: if ``True``, allow exporting definitions in
            ``__all__`` even if they have been imported from another module
            (default: ``False``)
        """
        self._globals = globals_
        self._imported = set(globals_.keys())

        try:
            self._module = module = globals_["__name__"]
        except KeyError:
            raise ValueError("arg globals_ does not define module name in __name__")

        if not public_module:
            public_module = public_module_prefix(module)

        self.public_module = globals_["__publicmodule__"] = public_module

        self.update_forward_references = update_forward_references
        self.allow_global_constants = allow_global_constants
        self.allow_imported_definitions = allow_imported_definitions

    #: Full name of the public module that will export the items managed by this
    #: tracker.
    public_module: str

    def validate(self) -> None:
        """
        Validate that all eligible items that were defined since the creation of this
        tracker are listed in the ``__all__`` variable.

        :raise AssertionError: if ``__all__`` is not as expected, or if one or more
            definitions do not meet the required criteria to be exported (
        """
        all_expected = self.get_tracked()

        globals_ = self._globals

        if set(globals_.get("__all__", [])) != set(all_expected):
            raise AssertionError(
                "missing or unexpected all declaration, "
                f"expected:\n__all__ = {all_expected}"
            )

        module = self._module
        public_module = self.public_module
        allow_global_constants = self.allow_global_constants
        forbid_imported_definitions = not self.allow_imported_definitions

        for name in all_expected:
            obj = globals_[name]

            # check that the object was defined locally
            try:
                obj_module = obj.__module__
            except AttributeError:
                if allow_global_constants:
                    obj_module = None
                else:
                    raise AssertionError(
                        f"exporting a global constant is not permitted: {obj!r}"
                    )

            if forbid_imported_definitions and obj_module and obj_module != module:
                raise AssertionError(
                    f"{_qualname(obj)} is exported by module {module} "
                    f"but defined in module {obj_module}"
                )

            # set public module field
            try:
                obj.__publicmodule__ = public_module
            except AttributeError:
                # objects without a __dict__ will not permit setting the public module
                pass

            if self.update_forward_references:
                # update forward references in annotations
                update_forward_references(obj, globals_=globals_)

    def get_tracked(self) -> List[str]:
        """
        List the names of all locally tracked, public items.

        :return: the list of object names, sorted alphabetically
        """
        return sorted(filter(self._is_eligible, self._globals))

    def is_tracked(self, name: str, item: Any) -> bool:
        """
        Check if the given item is tracked by this tracker under the given name.

        :param name: the name of the item in the tracker's global namespace
        :param item: the item referred to by the name
        :return: ``True`` if the given item is tracked by this tracker under the given
            name; ``False`` otherwise
        """
        try:
            return self._globals[name] is item and self._is_eligible(name)
        except KeyError:
            return False

    def _is_eligible(self, name: str) -> bool:
        # check if the given item is eligible for tracking by this tracker
        return not (name.startswith("_") or name in self._imported)

    def __getitem__(self, name: str) -> Any:
        # get a tracked item by name

        item = self._globals[name]
        if self._is_eligible(name=name):
            return item
        else:
            raise KeyError(name)


# regular expression to extract the public prefix of a private module
# this is the module path up to the first submodule with a leading underscore
# noinspection RegExpUnnecessaryNonCapturingGroup
__RE_PUBLIC_MODULE = re.compile(
    # start of match group for the public part of the module path
    r"("
    # first module component must not start with '_')
    r"(?:[a-zA-Z]\w+)"
    # then as many path components as can be matched non-greedily …)
    r"(?:\.\w+)*?"
    # but when we hit the first private path component, we stop matching the
    # public part of the path …
    r")"
    # … and match the rest as the private path
    r"(?:\._\w*(?:\.\w+)*)?"
)


def public_module_prefix(module_name: str) -> str:
    """
    Get the public prefix of the given module name.

    A module name is composed of one or more identifiers, separated by ``.`` operators.
    The public prefix is the module name including all identifiers up to, and excluding,
    the first identifier starting with an underscore character (``_``) .
    If there is no such identifier, then the public prefix is the same as the full
    module name.
    If the first identifier starts with a ``_``, then the public prefix is not defined.

    For example:

    - the public module prefix of ``a.b._c.d._e`` is ``a.b``
    - the public module prefix of ``a.b`` is ``a.b``
    - the public module prefix of ``_a.b.c`` is undefined

    :param module_name: the module name for which to get the public prefix
    :return: the public prefix
    :raise ValueError: the public prefix is undefined
    """
    match = __RE_PUBLIC_MODULE.fullmatch(module_name)
    if not match:
        raise ValueError(f"cannot infer public module path from module {module_name}")
    return match[1]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())
# we forget that class AllTracker itself is already defined, because we want to include
# it in the __all__ statement
# noinspection PyProtectedMember
__tracker._imported.remove(AllTracker.__name__)
# noinspection PyProtectedMember
__tracker._imported.remove(public_module_prefix.__name__)


def update_forward_references(
    obj: Union[type, FunctionType], *, globals_: Dict[str, Any]
) -> None:
    """
    Replace all forward references with their referenced classes.

    :param obj: a function or class
    :param globals_: a global namespace to search the referenced classes in
    """

    try:
        my_module = obj.__module__
    except AttributeError:
        # the object cannot be a type or function; no action required
        return

    # keep track of classes we already visited to prevent infinite recursion
    visited: Set[type] = set()

    def _update(_obj: Any, local_ns: Optional[Dict[str, Any]] = None) -> None:
        if isinstance(_obj, type) and _obj.__module__ == my_module:
            if _obj not in visited:
                visited.add(_obj)
                local_ns = dict(_obj.__dict__)
                for member in vars(_obj).values():
                    _update(member, local_ns=local_ns)
                _update_annotations(_obj, local_ns)

        elif isinstance(_obj, FunctionType) and _obj.__module__ == my_module:
            _update_annotations(_obj, local_ns)

    def _update_annotations(_obj: Any, local_ns: Optional[Dict[str, Any]]) -> None:
        annotations = get_type_hints(
            _obj, globalns=getattr(_obj, "__globals__", globals_), localns=local_ns
        )
        if annotations:
            _obj.__annotations__ = annotations

    _update(obj)


__tracker.validate()


#
# Auxiliary functions
#


def _qualname(_obj: Any) -> str:
    name: str

    try:
        name = _obj.__qualname__
    except AttributeError:
        try:
            name = _obj.__name__
        except AttributeError:
            name = repr(_obj)

    return name
