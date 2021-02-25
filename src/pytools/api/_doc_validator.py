"""
Core implementation of :class:`pytools.api.DocValidator`.
"""

import importlib
import inspect
import logging
import os
import re
from glob import glob
from inspect import Signature
from types import FunctionType, ModuleType
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from pytools.api import AllTracker, to_tuple

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["DocValidator"]


#
# Type variables
#

T = TypeVar("T")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class DocValidator:
    """
    Validates docstrings in all Python sources in a given directory tree.

    By default, only validates public classes, methods, and functions.
    Protected classes, methods, and functions are only validated if their name
    is provided in parameter ``validate_protected``.
    """

    #: the root directory of all Python files to be validated
    root_dir: str

    #: names of protected functions and methods to be validated
    validate_protected: Tuple[str, ...]

    #: names of modules for which parameter documentation and type hints should not be
    #: validated
    exclude_from_parameter_validation: re.Pattern

    #: after validation, lists the names of all modules with missing docstrings
    modules_with_missing_doc: List[str]

    #: after validation, lists the full names of all classes with missing docstrings
    classes_with_missing_doc: List[str]

    #: after validation, lists the full names of all functions and methods with
    #: missing docstrings
    functions_with_missing_doc: List[str]

    #: after validation, lists the full names of all functions and methods where
    #: the documented parameters do not match the actual parameters
    functions_with_mismatched_parameter_doc: List[str]

    #: after validation, lists the full names of all functions and methods whose
    #: signature is not fully type-hinted
    functions_with_missing_type_annotations: List[str]

    #: default value for
    VALIDATE_PROTECTED_DEFAULT = ("__init__",)

    #: name of the special "return" parameter used in signatures and type annotations
    _PARAM_RETURN = "return"

    def __init__(
        self,
        *,
        root_dir: str,
        validate_protected: Optional[Iterable[str]] = None,
        exclude_from_parameter_validation: Optional[Union[str, re.Pattern]] = None,
    ) -> None:
        """
        :param root_dir: the root directory of all Python files to be validated
        :param validate_protected: names of protected functions and methods to be
            validated (default: ``%VALIDATE_PROTECTED%``)
        :param exclude_from_parameter_validation: do not validate parameter
            documentation and type hints for classes, methods or functions whose full
            name (including the module prefix) matches the given regular expression
        """
        self.root_dir = root_dir
        self.validate_protected = to_tuple(
            validate_protected or self.VALIDATE_PROTECTED_DEFAULT,
            element_type=str,
        )
        self.exclude_from_parameter_validation = (
            exclude_from_parameter_validation
            if (
                exclude_from_parameter_validation is None
                or isinstance(exclude_from_parameter_validation, re.Pattern)
            )
            else re.compile(exclude_from_parameter_validation)
        )

        if not all(name.startswith("_") for name in self.validate_protected):
            raise ValueError("all names in arg validate_protected must start with'_'")

        self.modules_with_missing_doc = []
        self.classes_with_missing_doc = []
        self.functions_with_missing_doc = []
        self.functions_with_mismatched_parameter_doc = []
        self.functions_with_missing_type_annotations = []

    __init__.__doc__ = __init__.__doc__.replace(
        "%VALIDATE_PROTECTED%", repr(VALIDATE_PROTECTED_DEFAULT)
    )

    def validate_docstrings(self) -> bool:
        """
        Run the validation.

        :return: ``True`` if the validation was successful; ``False`` if the validation
            failed
        """

        modules = self._load_modules()

        if not modules:
            raise ValueError("no Python modules found")

        for module in modules:

            attributes = [
                getattr(module, name)
                for name in dir(module)
                if not name.startswith("_")
            ]

            module_name = module.__name__

            if not self.has_docstring(module):
                self.modules_with_missing_doc.append(module_name)

            self._validate_members(module_name=module_name, members=attributes)

        self._log_validation_errors()

        return not (
            self.modules_with_missing_doc
            or self.classes_with_missing_doc
            or self.functions_with_missing_doc
            or self.functions_with_mismatched_parameter_doc
            or self.functions_with_missing_type_annotations
        )

    @staticmethod
    def has_docstring(obj: Any) -> bool:
        """
        Check if __doc__ is missing or empty

        :param obj: object to check
        :return: ``True`` if docstring is present; ``False`` otherwise
        """
        doc = getattr(obj, "__doc__", None)
        if doc and str(doc).strip():
            return True
        else:
            if isinstance(obj, ModuleType):
                obj_name = f"module {obj.__name__}"
            else:
                obj_name = f"{obj.__module__}.{obj.__qualname__}"
            log.warning(f"Missing docstring for {obj_name}")
            return False

    @staticmethod
    def has_matching_parameter_doc(
        module_name: str, callable_obj: FunctionType
    ) -> bool:
        """
        Check if parameters match between a callable's signature and its docstring

        :param module_name: Name of the module/class the callable appears in (for log)
        :param callable_obj: the callable to check
        :return: ``True`` if parameters match; ``False`` otherwise
        """
        documented_parameters = DocValidator.list_documented_parameters(
            getattr(callable_obj, "__doc__", None) or ""
        )

        actual_parameters = DocValidator.list_actual_parameters(callable_obj)

        if actual_parameters != documented_parameters:
            log.warning(
                "Mismatched arguments in docstring for "
                f"{module_name}.{callable_obj.__qualname__}: "
                f"expected {actual_parameters} but got {documented_parameters}"
            )
            return False
        else:
            return True

    @staticmethod
    def is_type_hinted(module_name: str, callable_obj: FunctionType) -> bool:
        """
        Check if the given function is fully type hinted.

        :param module_name: Name of the module/class the callable appears in (for log)
        :param callable_obj: the callable to check
        :return: ``True`` if fully type hinted; ``False`` otherwise
        """
        annotations = callable_obj.__annotations__
        parameters_without_annotations = {
            parameter
            for parameter in DocValidator._get_parameters(
                signature=inspect.signature(callable_obj)
            )
            if parameter not in annotations
        }
        if parameters_without_annotations:
            log.warning(
                f"Function {module_name}.{callable_obj.__qualname__} "
                "lacks type annotations for parameters "
                f"{parameters_without_annotations}"
            )
        has_return_annotation = DocValidator._PARAM_RETURN in annotations
        if not has_return_annotation:
            log.warning(
                f"Function {module_name}.{callable_obj.__qualname__} "
                "lacks type annotation for return value"
            )

        return has_return_annotation and not parameters_without_annotations

    @staticmethod
    def list_documented_parameters(docstring: str) -> List[str]:
        """
        Extract all documented parameter names from a docstring, including ``return``
        if the return parameter is documented.

        :param docstring: the input docstring
        :return: list of parameter names
        """
        all_params = re.findall(
            pattern=r"\:param\s+(\w+)\s*\:|\:(return)s?:",
            string=docstring,
            flags=re.MULTILINE,
        )

        return [p[0] or p[1] for p in all_params]

    @staticmethod
    def list_actual_parameters(callable_obj: FunctionType) -> List[str]:
        """
        Extract all parameter names from a function signature, including ``return``
        if there is a type hint for a return parameter.

        :param callable_obj: the function for which to get the signature
        :return: list of parameter names
        """
        signature: Signature = inspect.signature(callable_obj)
        actual_parameters = DocValidator._get_parameters(signature)
        if not (
            signature.return_annotation is signature.empty
            or signature.return_annotation is None
        ):
            actual_parameters.append(DocValidator._PARAM_RETURN)
        return actual_parameters

    @staticmethod
    def _get_parameters(signature: Signature) -> List[str]:
        return [
            parameter
            for i, parameter in enumerate(signature.parameters.keys())
            if i > 0 or parameter not in {"self", "cls"}
        ]

    def _validate_members(self, module_name: str, members: Collection[Any]) -> None:
        def _filter_excluded(kind: Type[T]) -> Dict[str, T]:
            named_objects = (
                (f"{module_name}.{obj.__qualname__}", obj)
                for obj in members
                if isinstance(obj, kind)
            )
            if self.exclude_from_parameter_validation:
                return {
                    name: obj
                    for name, obj in named_objects
                    if not self.exclude_from_parameter_validation.match(name)
                }
            else:
                return dict(named_objects)

        classes = _filter_excluded(kind=type)
        functions = _filter_excluded(kind=FunctionType)

        # classes where docstring is missing
        self.classes_with_missing_doc.extend(
            name for name, cls in classes.items() if not self.has_docstring(cls)
        )
        # functions where docstring is missing
        # (except __init__ - shares docstring with class)
        self.functions_with_missing_doc.extend(
            name
            for name, func in functions.items()
            if func.__name__ != "__init__" and not self.has_docstring(func)
        )
        self.functions_with_mismatched_parameter_doc.extend(
            name
            for name, func in functions.items()
            if not DocValidator.has_matching_parameter_doc(
                module_name=module_name, callable_obj=func
            )
        )
        self.functions_with_missing_type_annotations.extend(
            name
            for name, func in functions.items()
            if not self.is_type_hinted(module_name=module_name, callable_obj=func)
        )

        validate_protected = self.validate_protected

        def _filter_protected(name: str) -> bool:
            return name in validate_protected or not name.startswith("_")

        # inspect classes recursively
        for cls in classes.values():
            self._validate_members(
                module_name=module_name,
                members=[
                    attribute
                    for name, attribute in vars(cls).items()
                    if _filter_protected(name)
                ],
            )

    def _log_validation_errors(self) -> None:
        def _lines(s: Iterable[str]) -> str:
            return "\n".join(s)

        if self.modules_with_missing_doc:
            log.warning(
                "One or more modules lack docstrings:\n"
                + _lines(self.modules_with_missing_doc)
            )
        if self.classes_with_missing_doc:
            log.warning(
                "One or more classes lack docstrings:\n"
                + _lines(self.classes_with_missing_doc)
            )
        if self.functions_with_missing_doc:
            log.warning(
                "One or more functions lack docstrings:\n"
                + _lines(self.functions_with_missing_doc)
            )
        if self.functions_with_mismatched_parameter_doc:
            log.warning(
                "One or more functions have mismatched parameter documentation:\n"
                + _lines(self.functions_with_mismatched_parameter_doc)
            )
        if self.functions_with_mismatched_parameter_doc:
            log.warning(
                "One or more functions lack type hints:\n"
                + _lines(self.functions_with_missing_type_annotations)
            )

    def _load_modules(self) -> List[ModuleType]:
        # list paths to all python files
        suffix = ".py"
        root_dir = self.root_dir
        prefix_len = len(root_dir) + len(os.sep)
        suffix_len = len(suffix)

        return [
            importlib.import_module(module_path)
            for module_path in (
                path[prefix_len:-suffix_len]
                .replace(os.sep, ".")
                .replace(".__init__", "")
                for path in glob(
                    os.path.join(root_dir, "**", f"*{suffix}"), recursive=True
                )
            )
            if not module_path[module_path.rfind(".") + 1 :].startswith("_")
        ]


__tracker.validate()
