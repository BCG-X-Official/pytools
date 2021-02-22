import importlib
import inspect
import logging
import os
import re
from glob import glob
from types import FunctionType, ModuleType
from typing import Any, Collection, Iterable, List, Optional

log = logging.getLogger(__name__)


class DocValidator:
    root_dir: str

    classes_with_missing_doc: List[str]
    functions_with_missing_doc: List[str]
    functions_with_mismatched_parameter_doc: List[str]

    VALIDATE_PROTECTED_DEFAULT = ("__init__",)

    def __init__(
        self, root_dir: str, validate_protected: Optional[Collection[str]] = None
    ) -> None:
        self.root_dir = root_dir
        self.validate_protected = (
            validate_protected
            if validate_protected
            else self.VALIDATE_PROTECTED_DEFAULT
        )

        self.classes_with_missing_doc = []
        self.functions_with_missing_doc = []
        self.functions_with_mismatched_parameter_doc = []

    def validate_docstrings(self) -> bool:

        modules = self._load_modules()

        if not modules:
            raise ValueError("no Python modules found")

        for module in modules:

            attributes = [
                getattr(module, name)
                for name in dir(module)
                if not name.startswith("_")
            ]

            self._validate_members(module_name=module.__name__, members=attributes)

        def lines(s: Iterable[str]) -> str:
            return "\n".join(s)

        if self.classes_with_missing_doc:
            log.warning(
                "One or more classes lack docstrings:\n"
                + lines(self.classes_with_missing_doc)
            )

        if self.functions_with_missing_doc:
            log.warning(
                "One or more functions lack docstrings:\n"
                + lines(self.functions_with_missing_doc)
            )

        if self.functions_with_mismatched_parameter_doc:
            log.warning(
                "One or more functions have mismatched parameter documentation:\n"
                + lines(self.functions_with_mismatched_parameter_doc)
            )

        return not (
            self.classes_with_missing_doc
            or self.functions_with_missing_doc
            or self.functions_with_mismatched_parameter_doc
        )

    @staticmethod
    def is_docstring_missing(obj: Any) -> bool:
        """
        Check if __doc__ is missing or empty

        :param obj: object to check
        :return: boolean if docstr is missing
        """
        doc = getattr(obj, "__doc__", None)
        return not (doc and str(doc).strip())

    @staticmethod
    def is_parameter_doc_mismatched(module_name: str, callable_obj: callable) -> bool:
        """
        Check if parameters are inconsistent between a callable's signature and docstr

        :param module_name: Name of the module/class the callable appears in (for log)
        :param callable_obj: the callable to check
        :return: True if inconsistent, else False
        """
        documented_parameters = DocValidator.list_documented_parameters(
            str(callable_obj.__doc__)
        )

        actual_parameters = DocValidator.list_actual_parameters(callable_obj)

        if actual_parameters == documented_parameters:
            return False

        log.warning(
            "Mismatched arguments in docstring for "
            f"{module_name}.{callable_obj.__qualname__}: "
            f"expected {actual_parameters} but got {documented_parameters}"
        )

        return True

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
    def list_actual_parameters(callable_obj: callable) -> List[str]:
        """
        Extract all parameter names from a function signature, including ``return``
        if there is a type hint for a return parameter.

        :param callable_obj: the function for which to get the signature
        :return: list of parameter names
        """
        signature = inspect.signature(callable_obj)
        actual_parameters = list(signature.parameters.keys())
        if actual_parameters and actual_parameters[0] in ["self", "cls"]:
            del actual_parameters[0]
        if not (
            signature.return_annotation is signature.empty
            or signature.return_annotation is None
        ):
            actual_parameters.append("return")
        return actual_parameters

    def _validate_members(self, module_name: str, members: Collection[Any]) -> None:
        def full_name(name: str) -> str:
            return f"{module_name}.{name}"

        classes = [cls for cls in members if isinstance(cls, type)]
        functions = [func for func in members if isinstance(func, FunctionType)]

        # classes where docstring is missing
        self.classes_with_missing_doc.extend(
            full_name(cls.__qualname__)
            for cls in classes
            if self.is_docstring_missing(cls)
        )
        # functions where docstring is missing
        # (except __init__ - shares docstring with class)
        self.functions_with_missing_doc.extend(
            full_name(func.__qualname__)
            for func in functions
            if self.is_docstring_missing(func) and func.__name__ != "__init__"
        )
        self.functions_with_mismatched_parameter_doc.extend(
            full_name(func.__qualname__)
            for func in functions
            if (
                not self.is_docstring_missing(func)
                and self.is_parameter_doc_mismatched(
                    module_name=module_name, callable_obj=func
                )
            )
        )

        # inspect classes recursively
        for cls in classes:
            self._validate_members(
                module_name=module_name,
                members=[
                    attribute
                    for name, attribute in vars(cls).items()
                    if self._filter_protected(name)
                ],
            )

    def _filter_protected(self, name: str) -> bool:
        return name in self.validate_protected or not name.startswith("_")

    def _load_modules(self) -> List[ModuleType]:
        # list paths to all python files
        suffix = ".py"
        root_dir = self.root_dir
        prefix_len = len(root_dir) + len(os.sep)
        suffix_len = len(suffix)

        return [
            importlib.import_module(module_path)
            for module_path in (
                path.replace(os.sep, ".").replace(".__init__", "")
                for path in [
                    path1[prefix_len:-suffix_len]
                    for path1 in glob(
                        os.path.join(root_dir, "**", f"*{suffix}"), recursive=True
                    )
                ]
            )
            if self._filter_protected(module_path[module_path.rfind(".") + 1 :])
        ]


def test_docstrings() -> None:
    assert DocValidator(root_dir="src").validate_docstrings(), "docstrings are valid"
