"""
Core implementation of :mod:`pytools.api.doc`.
"""

import inspect
import logging
import re
from abc import ABCMeta, abstractmethod
from inspect import Signature
from types import FunctionType, ModuleType
from typing import Generic, List, Optional, TypeVar, Union

from pytools.api import AllTracker, inheritdoc

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = [
    "DocTest",
    "NamedElementDefinition",
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
    def public_module(self) -> str:
        """
        The public module that exposes the API definition.
        This may not necessarily be the same as the module in which the element
        is actually defined.
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

    def list_documented_parameters(self) -> Optional[List[str]]:
        """
        Extract all documented parameter names from the docstring, including
        ``"return"`` if the return parameter is documented.

        :return: list of parameter names
        """

        docstring = self.docstring

        if docstring is None:
            return None

        all_params = re.findall(
            pattern=r"\:param\s+(\w+)\s*\:|\:(return)s?:",
            string=docstring,
            flags=re.MULTILINE,
        )

        return [param[0] or param[1] for param in all_params]

    def __str__(self) -> str:
        return self.full_name


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
    def public_module(self) -> str:
        """[see superclass]"""
        return self.name

    @property
    def full_name(self) -> str:
        """[see superclass]"""
        return self.name

    @property
    def docstring(self) -> Optional[str]:
        """[see superclass]"""
        return self.module.__doc__

    def __repr__(self) -> str:
        """[see superclass]"""
        return f"{type(self).__name__}({self.module!r})"


@inheritdoc(match="""[see superclass]""")
class NamedElementDefinition(APIDefinition, Generic[T]):
    """
    A reference to a Python class or function definition.
    """

    #: the class or function
    element: T

    def __init__(self, element: T, *, public_module: Optional[str] = None) -> None:
        """
        :param element: the API element
        :param public_module: the public module exposing the element; this can be
            different from a private module containing the actual definition of the
            element
        """
        self.element = element
        self._public_module = public_module or element.__module__

    @property
    def name(self) -> str:
        """[see superclass]"""
        return self.element.__name__

    @property
    def public_module(self) -> str:
        """[see superclass]"""
        return self._public_module

    @property
    def full_name(self) -> str:
        """[see superclass]"""
        element = self.element
        return f"{self._public_module}.{element.__qualname__}"

    @property
    def docstring(self) -> Optional[str]:
        """[see superclass]"""
        return self.element.__doc__

    def __repr__(self) -> str:
        args = repr(self.element)
        if self._public_module is not self.element.__module__:
            args += f", public_module={self._public_module!r}"
        return f"{type(self).__name__}({args})"


class FunctionDefinition(NamedElementDefinition[FunctionType]):
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

        if (
            documented_parameters is not None
            and actual_parameters != documented_parameters
        ):
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


__tracker.validate()
