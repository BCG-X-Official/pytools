"""
Core implementation of :class:`pytools.api.DocValidator`.
"""

import importlib
import inspect
import logging
import os
import re
import sys
from abc import ABCMeta, abstractmethod
from glob import glob
from inspect import Signature
from types import FunctionType, ModuleType
from typing import (
    Any,
    Collection,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from pytools.api import AllTracker, inheritdoc, to_tuple

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = [
    "DocTest",
    "DocValidator",
    "ElementDefinition",
    "FunctionDefinition",
    "HasDocstring",
    "HasMatchingParameterDoc",
    "HasTypeHints",
    "HasWellFormedDocstring",
    "ModuleDefinition",
    "APIDefinition",
]

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


class APIDefinition(metaclass=ABCMeta):
    """
    A reference to the definition of an API element, e.g., a module, class, or function.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of this API element.
        """

    @property
    @abstractmethod
    def full_name(self) -> str:
        """
        The full name of this API element, including the full module name and containing
        element names.
        """

    @property
    @abstractmethod
    def docstring(self) -> Optional[str]:
        """
        The docstring of this API element; ``None`` if the docstring is undefined.
        """

    def list_documented_parameters(self) -> List[str]:
        """
        Extract all documented parameter names from the docstring, including ``return``
        if the return parameter is documented.

        :return: list of parameter names
        """

        docstring = self.docstring

        if not docstring:
            return []

        all_params = re.findall(
            pattern=r"\:param\s+(\w+)\s*\:|\:(return)s?:",
            string=docstring,
            flags=re.MULTILINE,
        )

        return [param[0] or param[1] for param in all_params]


@inheritdoc(match="""[see superclass]""")
class ModuleDefinition(APIDefinition):
    """
    A reference to a Python module definition.
    """

    #: the module
    module: ModuleType

    def __init__(self, module: ModuleType) -> None:
        """
        :param module: the module
        """
        self.module = module

    @property
    def name(self) -> str:
        """[see superclass]"""
        return self.module.__name__

    @property
    def full_name(self) -> str:
        """[see superclass]"""
        return self.module.__name__

    @property
    def docstring(self) -> Optional[str]:
        """[see superclass]"""
        return self.module.__doc__


@inheritdoc(match="""[see superclass]""")
class ElementDefinition(APIDefinition, Generic[T]):
    """
    A reference to a Python class or function definition.
    """

    #: the class or function
    element: T

    def __init__(self, element: T) -> None:
        """
        :param element: the API element
        """
        self.element = element

    @property
    def name(self) -> str:
        """[see superclass]"""
        return self.element.__name__

    @property
    def full_name(self) -> str:
        """[see superclass]"""
        element = self.element
        return f"{element.__module__}.{element.__qualname__}"

    @property
    def docstring(self) -> Optional[str]:
        """[see superclass]"""
        return self.element.__doc__


@inheritdoc(match="""[see superclass]""")
class FunctionDefinition(ElementDefinition[FunctionType]):
    """
    A reference to a Python function definition.
    """

    #: name of the special "return" parameter used in signatures and type annotations
    PARAM_RETURN = "return"

    def list_actual_parameters(self, include_return: bool) -> List[str]:
        """
        Extract all parameter names from the function signature

        :param include_return: include ``return`` as final parameter
            if there is a type hint for a return parameter
        :return: list of parameter names
        """

        signature: Signature = inspect.signature(self.element)

        actual_parameters = [
            parameter
            for i, parameter in enumerate(signature.parameters.keys())
            if i > 0 or parameter not in {"self", "cls"}
        ]

        if include_return and not (
            signature.return_annotation is signature.empty
            or signature.return_annotation is None
        ):
            actual_parameters.append(FunctionDefinition.PARAM_RETURN)

        return actual_parameters


class DocTest(metaclass=ABCMeta):
    """
    A test to be run on the documentation of all API elements, including docstrings and
    type hints.
    """

    @abstractmethod
    def test(self, definition: APIDefinition) -> Union[None, str, List[str]]:
        """
        Test the given definition.

        :param definition: the definition to test
        :return: an error test or list of error texts if the definition failed;
            ``None`` or an empty list if successful
        """
        pass


@inheritdoc(match="""[see superclass]""")
class HasDocstring(DocTest):
    """
    Test that the definition's docstring is defined and not empty.
    """

    def test(self, definition: APIDefinition) -> Union[None, str, List[str]]:
        """[see superclass]"""

        doc = definition.docstring
        if not (doc and str(doc).strip()) and not definition.name == "__init__":
            return "missing docstring"
        else:
            return None


@inheritdoc(match="""[see superclass]""")
class HasMatchingParameterDoc(DocTest):
    """
    Check if parameters match between a callable's signature and its docstring.
    """

    def test(self, definition: APIDefinition) -> Union[None, str, List[str]]:
        """[see superclass]"""

        if not isinstance(definition, FunctionDefinition):
            return None

        actual_parameters = definition.list_actual_parameters(include_return=True)
        documented_parameters = definition.list_documented_parameters()

        if actual_parameters != documented_parameters:
            return (
                "mismatched arguments: "
                f"expected {actual_parameters} but got {documented_parameters}"
            )
        else:
            return None


@inheritdoc(match="""[see superclass]""")
class HasWellFormedDocstring(DocTest):
    """
    Check if the given element has a well-formed docstring.
    """

    def test(self, definition: APIDefinition) -> Union[None, str, List[str]]:
        """[see superclass]"""
        docstring = definition.docstring

        if not docstring:
            return None

        lines = list(map(str.rstrip, docstring.split("\n")))

        previous_line_text_indent = -1

        errors: List[str] = []

        for line in lines:

            if not line:
                previous_line_text_indent = -1
                continue

            line_elements = re.match(r"(\s*)(:(?:param|returns?|raises?))?", line)
            text_indent = line_elements.regs[1][1]

            is_param_line = text_indent < line_elements.regs[2][1]

            if 0 <= previous_line_text_indent <= text_indent and is_param_line:
                errors.append(f'missing blank line before line "{line.strip()}"')

            previous_line_text_indent = -1 if is_param_line else text_indent

        return errors


@inheritdoc(match="""[see superclass]""")
class HasTypeHints(DocTest):
    """
    Check if the given function is fully type hinted.
    """

    def test(self, definition: APIDefinition) -> Union[None, str, List[str]]:
        """[see superclass]"""

        if not isinstance(definition, FunctionDefinition):
            return None

        function = definition.element
        annotations = function.__annotations__
        errors: List[str] = []

        parameters_without_annotations = {
            parameter
            for parameter in definition.list_actual_parameters(include_return=False)
            if parameter not in annotations
        }

        if parameters_without_annotations:
            errors.append(
                "missing type annotation for parameters "
                f"{parameters_without_annotations}"
            )

        if FunctionDefinition.PARAM_RETURN not in annotations:
            errors.append("missing type annotation for return value")

        return errors


class DocValidator:
    """
    Validates docstrings and type hints in all Python sources in a given directory tree.

    By default, only validates public classes, methods, and functions, and
    class initializers (``__init__``).
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

    #: after validation, lists all errors per definition
    validation_errors: Dict[str, List[str]]

    #: tests to run on each definition during validation
    validation_tests: Tuple[DocTest]

    #: default value for parameter ``validate_protected``
    DEFAULT_VALIDATE_PROTECTED = ("__init__",)

    #: default doc tests to run
    DEFAULT_DOC_TESTS: Tuple[DocTest] = (
        HasDocstring(),
        HasMatchingParameterDoc(),
        HasWellFormedDocstring(),
        HasTypeHints(),
    )

    def __init__(
        self,
        *,
        root_dir: str,
        validate_protected: Optional[Iterable[str]] = None,
        exclude_from_parameter_validation: Optional[Union[str, re.Pattern]] = None,
        additional_tests: Optional[Iterable[DocTest]] = None,
    ) -> None:
        """
        :param root_dir: the root directory of all Python files to be validated
        :param validate_protected: names of protected functions and methods to be
            validated (default: ``%VALIDATE_PROTECTED%``)
        :param exclude_from_parameter_validation: do not validate parameter
            documentation and type hints for classes, methods or functions whose full
            name (including the module prefix) matches the given regular expression
        :param additional_tests: additional documentation tests to run on each API
            element
        """
        self.root_dir = root_dir
        self.validate_protected = to_tuple(
            validate_protected or self.DEFAULT_VALIDATE_PROTECTED,
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

        self.validation_errors = {}
        self.validation_tests = (
            tuple(*self.DEFAULT_DOC_TESTS, *additional_tests)
            if additional_tests
            else self.DEFAULT_DOC_TESTS
        )

    __init__.__doc__ = __init__.__doc__.replace(
        "%VALIDATE_PROTECTED%", repr(DEFAULT_VALIDATE_PROTECTED)
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

        self._run_tests(definitions=map(ModuleDefinition, modules))

        for module in modules:
            self._validate_members(
                members=[
                    getattr(module, name)
                    for name in dir(module)
                    if not name.startswith("_")
                ]
            )

        self._log_validation_errors()

        return not self.validation_errors

    def _run_tests(self, definitions: Iterable[APIDefinition]) -> None:
        """
        Run all validation tests on the given definitions, and store errors

        :param definitions: the definitions to run validation tests on
        """
        for definition in definitions:
            errors: List[str] = []
            for test in self.validation_tests:
                test_results = test.test(definition)
                if test_results:
                    if isinstance(test_results, str):
                        errors.append(test_results)
                    else:
                        errors.extend(test_results)
            if errors:
                self.validation_errors[definition.full_name] = errors

    def _validate_members(self, members: Collection[Any]) -> None:
        def _filter_excluded(
            kind: Type[T], definition_type: Type[ElementDefinition]
        ) -> Iterable[ElementDefinition]:
            definitions = (
                definition_type(obj) for obj in members if isinstance(obj, kind)
            )

            if self.exclude_from_parameter_validation:
                return filter(
                    lambda definition: not self.exclude_from_parameter_validation.match(
                        definition.full_name
                    ),
                    definitions,
                )
            else:
                return definitions

        classes: List[ElementDefinition] = list(
            _filter_excluded(kind=type, definition_type=ElementDefinition)
        )
        functions: Iterable[ElementDefinition] = _filter_excluded(
            kind=FunctionType, definition_type=FunctionDefinition
        )

        self._run_tests(functions)
        self._run_tests(classes)

        validate_protected = self.validate_protected

        def _filter_protected(name: str) -> bool:
            return name in validate_protected or not name.startswith("_")

        # inspect classes recursively
        for cls in classes:
            self._validate_members(
                members=[
                    attribute
                    for name, attribute in vars(cls.element).items()
                    if _filter_protected(name)
                ],
            )

    def _log_validation_errors(self) -> None:
        for full_name, errors in self.validation_errors.items():
            for error in errors:
                print(f"{full_name}: {error}", file=sys.stderr)

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
