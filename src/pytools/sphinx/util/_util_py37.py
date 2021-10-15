"""
Implementation of sphinx module.
"""
import importlib
import logging
from inspect import getattr_static
from types import FunctionType, MethodType
from typing import Any, Dict, Optional, Tuple, Type, TypeVar, Union, get_type_hints

import typing_inspect

from ...api import AllTracker, get_generic_bases, inheritdoc
from .. import AutodocBeforeProcessSignature

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["ResolveTypeVariables"]


#: Mock type declaration: Sphinx application object
Sphinx = Any


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


#
# Classes
#


class _TypeVarBindings:
    def __init__(self, current_class: type) -> None:
        self.current_class = current_class
        self._bindings = self._get_parameter_bindings(
            cls=current_class, subclass_bindings={}
        )

    def resolve_parameter(
        self, defining_class: type, parameter: TypeVar
    ) -> Union[Type, TypeVar]:
        """
        Resolve a type parameter, substituting it with an actual type if the parameter
        is bound to a type argument in the context of the current class;
        otherwise return the parameter unchanged.

        :param defining_class: the class that introduced the type parameter; this is
            the the current class itself, or a base class of the current class
        :param parameter: the type variable
        :return: the resolved parameter if bound to a type argument; else the original
            parameter as a type variable
        """
        return self._bindings.get(defining_class, {}).get(parameter, parameter)

    def _get_parameter_bindings(
        self,
        cls: type,
        subclass_bindings: Dict[TypeVar, Union[Type, TypeVar]] = None,
    ) -> Dict[Type, Dict[TypeVar, Union[Type, TypeVar]]]:
        # get type variable bindings for all generic types defined in the class
        # hierarchy of the given parent class, applying the given bindings derived from
        # child classes

        # if arg cls has generic type parameters, it will have a corresponding
        cls_origin: Optional[type] = None
        if typing_inspect.is_generic_type(cls):
            cls_origin: type = typing_inspect.get_origin(cls)

        if cls_origin:
            class_bindings: Dict[TypeVar, type] = {
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

    original_signatures: Dict[Any, Dict[str, Union[Type, TypeVar]]]

    _current_class_bindings: Optional[_TypeVarBindings]

    def __init__(self) -> None:
        self.original_signatures = {}
        self._current_class_bindings = None

    def _resolve_function_signature(
        self, bindings: _TypeVarBindings, func: FunctionType
    ) -> None:
        # get the class in which the method has been defined
        defining_class = self._get_defining_class(func)
        if defining_class is None:
            # no or unknown defining class: nothing to resolve in the signature
            return
        log.debug(f"function {func} was defined in {defining_class}")

        # get the original signature and convert it to a list of (name, type) tuples
        signature_original_items = list(self._get_original_signature(func).items())

        def _get_self_or_cls_type_substitution() -> Tuple[
            Optional[TypeVar], Optional[Type]
        ]:

            if signature_original_items:

                method_type = self._get_method_type(defining_class, func)

                if method_type is METHOD_TYPE_DYNAMIC:
                    # special case: we substitute type vars bound to the class
                    # when assigned to the 'self' or 'cls' parameters of methods
                    _, arg_0_type = signature_original_items[0]
                    if typing_inspect.is_typevar(arg_0_type):
                        return arg_0_type, bindings.current_class

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
        arg_0_substitute: Optional[Type]

        arg_0_type_var, arg_0_substitute = _get_self_or_cls_type_substitution()

        def _substitute_type_vars_in_type_expression(
            type_expression: Union[Type, TypeVar]
        ) -> type:
            # recursively substitute type vars with their resolutions
            if isinstance(type_expression, TypeVar):
                if type_expression == arg_0_type_var:
                    # special case: substitute a type variable introduced by the
                    # initial self/cls argument of a dynamic or class method
                    return arg_0_substitute
                else:
                    # resolve type variables defined by Generic[] in the
                    # class hierarchy
                    return bindings.resolve_parameter(defining_class, type_expression)
            else:
                # dynamically resolve type variables inside nested type expressions
                args = typing_inspect.get_args(type_expression)
                if args:
                    # noinspection PyUnresolvedReferences
                    return type_expression.copy_with(
                        tuple(map(_substitute_type_vars_in_type_expression, args))
                    )
                else:
                    return type_expression

        # get the actual signature object that we will modify
        signature = func.__annotations__
        if not signature:
            return

        for name, tp in signature_original_items:
            signature[name] = _substitute_type_vars_in_type_expression(tp)

    def _resolve_attribute_signatures(self, cls: Type) -> None:
        bindings: _TypeVarBindings = self._current_class_bindings

        def _substitute_type_vars_in_type_expression(
            type_expression: Union[Type, TypeVar]
        ) -> type:
            # recursively substitute type vars with their resolutions
            if isinstance(type_expression, TypeVar):
                # resolve type variables defined by Generic[] in the
                # class hierarchy
                return bindings.resolve_parameter(cls, type_expression)
            else:
                # dynamically resolve type variables inside nested type expressions
                args = typing_inspect.get_args(type_expression)
                if args:
                    # noinspection PyUnresolvedReferences
                    return type_expression.copy_with(
                        tuple(map(_substitute_type_vars_in_type_expression, args))
                    )
                else:
                    return type_expression

        annotations = getattr(cls, "__annotations__", None)
        if annotations:
            cls.__annotations__ = {
                attr: _substitute_type_vars_in_type_expression(annotation)
                for attr, annotation in annotations.items()
            }

    @staticmethod
    def _get_defining_class(method: FunctionType) -> Optional[type]:
        # get the class that defined the callable

        if "." not in method.__qualname__:
            # this is a function, not a method
            return

        method_container: str
        if method.__qualname__.endswith(f".{method.__name__}"):
            method_container = method.__qualname__[: -len(method.__name__) - 1]
        else:
            method_container = method.__qualname__[: method.__qualname__.rfind(".")]

        try:
            return eval(
                method_container, importlib.import_module(method.__module__).__dict__
            )
        except NameError:
            # we could not find the container of the given method in the method's global
            # namespace - this is likely an inherited method where the parent class
            #
            log.warning(
                f"failed to find container {method.__module__}.{method_container!r} "
                f"of method {method.__name__!r}"
            )
            return None

    @staticmethod
    def _get_method_type(defining_class: type, func: FunctionType) -> int:
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
    ) -> Dict[str, Union[type, TypeVar]]:
        # get the original signature as defined in the code
        signature_original: Dict[str, Union[type, TypeVar]]
        try:
            signature_original = self.original_signatures[func]
        except KeyError:
            signature_original = get_type_hints(func)
            self.original_signatures[func] = signature_original
        return signature_original

    def process(self, app: Sphinx, obj: Any, bound_method: bool) -> None:
        """[see superclass]"""

        if isinstance(obj, type):
            # we are starting to process a new class, remember it so we can
            # attribute unbound methods to it
            self._update_current_class(obj)

        elif isinstance(obj, FunctionType):
            bindings = self._update_current_class(self._get_defining_class(obj))

            # instance method definitions are unbound, so we need to remember
            # the class we are currently in
            if bindings is not None:
                self._resolve_function_signature(bindings=bindings, func=obj),

        elif isinstance(obj, MethodType):
            # class method definitions are bound, so we can infer the current class
            cls = obj.__self__
            assert isinstance(cls, type), "methods are class methods"
            self._resolve_function_signature(
                bindings=self._update_current_class(cls), func=obj.__func__
            )

    def _update_current_class(self, cls: Optional[type]) -> Optional[_TypeVarBindings]:
        if cls is None:
            return None

        bindings = self._current_class_bindings
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
