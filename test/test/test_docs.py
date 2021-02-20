import importlib
import inspect
import logging
import os
import re
from glob import glob
from types import ModuleType
from typing import Any, Iterable, List, Tuple

log = logging.getLogger(__name__)


class DocValidator:
    root_dir: str

    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir

    def _list_python_files(self) -> List[str]:
        # list paths to all python files
        suffix = ".py"
        root_dir = self.root_dir
        prefix_len = len(root_dir) + len(os.sep)
        suffix_len = len(suffix)

        return [
            path[prefix_len:-suffix_len]
            for path in glob(os.path.join(root_dir, "**", f"*{suffix}"), recursive=True)
        ]

    def _list_modules(self) -> List[ModuleType]:
        """
        Dynamically import all Python modules in the codebase

        :return: list of imported Python modules as objects
        """

        return [
            importlib.import_module(module)
            for module in (
                path.replace(os.sep, ".").replace(".__init__", "")
                for path in self._list_python_files()
            )
        ]

    @staticmethod
    def list_members(
        member: Any,
    ) -> Tuple[
        List[Tuple[str, object]], List[Tuple[str, object]], List[Tuple[str, object]]
    ]:
        """
        Return children of a given member (module, class,..)
        :param member: a Python module or class
        :return: three lists for classes, functions and methods
        """

        if inspect.ismodule(member):
            module = member.__name__
        else:
            module = member.__module__

        all_children = [
            (name, obj)
            for name, obj in inspect.getmembers(member)
            if getattr(obj, "__module__", None) == module
        ]

        classes = [(name, obj) for name, obj in all_children if inspect.isclass(obj)]
        functions = [
            (name, obj) for name, obj in all_children if inspect.isfunction(obj)
        ]
        methods = [(name, obj) for name, obj in all_children if inspect.ismethod(obj)]

        return classes, functions, methods

    @staticmethod
    def docstring_missing(obj_name: str, obj: object) -> bool:
        """
        Check if __doc__ is missing or empty
        :param obj_name: name of the object to check
        :param obj: object to check
        :return: boolean if docstr is missing
        """
        if obj_name.startswith("_"):
            return False

        doc = getattr(obj, "__doc__", None)
        return not (doc and str(doc).strip())

    @staticmethod
    def extract_params_from_docstr(docstr: str) -> List[str]:
        """
        Extract all documented parameter names from a docstring

        :param docstr: the input docstring
        :return: list of parameter names
        """
        all_params = re.findall(
            pattern=r"(\:param\s+)(\w+)(\:)", string=docstr, flags=re.MULTILINE
        )

        return [p[1].strip() for p in all_params]

    def parameters_inconsistent(
        self, parent: str, call_obj_name: str, call_obj: object
    ) -> bool:
        """
        Check if parameters are inconsistent between a callable's signature and docstr

        :param parent: Name of the module/class the callable appears in (for log)
        :param call_obj_name: the name of the callable to check
        :param call_obj: the callable to check
        :return: True if inconsistent, else False
        """
        docstr_params = self.extract_params_from_docstr(str(call_obj.__doc__))
        full_args = inspect.getfullargspec(call_obj)
        func_args = full_args.args

        if "self" in func_args:
            func_args.remove("self")

        if docstr_params is not None and len(docstr_params) > 0:

            for idx, f_arg in enumerate(func_args):
                if idx >= len(docstr_params) or docstr_params[idx] != f_arg:
                    log.info(
                        f"Wrong arguments in docstring for {parent}.{call_obj_name}: "
                        f"{f_arg}"
                    )
                    return True
        else:
            # the function has arguments defined but none were found from __doc__?
            if len(full_args.args) > 0:
                log.info(
                    f"No documented arguments in docstring for {parent}.{call_obj_name}"
                )
                return True

        # all ok
        return False

    def validate_docstrings(self) -> None:

        modules: List[ModuleType] = self._list_modules()

        if not modules:
            raise ValueError("no Python modules found")

        classes_with_missing_docstr = []
        functions_with_missing_docstr = []
        methods_with_missing_docstr = []
        inconsistent_parameters = []

        for module in modules:
            module_name = module.__name__

            def full_name(name: str) -> str:
                return f"{module_name}.{name}"

            classes, functions, methods = self.list_members(module)

            # classes where docstring is None:
            classes_with_missing_docstr.extend(
                full_name(name)
                for name, obj in classes
                if self.docstring_missing(name, obj)
            )

            # functions where docstring is None:
            functions_with_missing_docstr.extend(
                full_name(name)
                for name, obj in functions
                if self.docstring_missing(name, obj)
            )

            # methods where docstring is None:
            methods_with_missing_docstr.extend(
                full_name(name)
                for name, obj in methods
                if self.docstring_missing(name, obj)
            )

            inconsistent_parameters.extend(
                full_name(name)
                for name, func in functions
                if not (name.startswith("_") or self.docstring_missing(name, func))
                and self.parameters_inconsistent(
                    parent=module_name, call_obj_name=name, call_obj=func
                )
            )

            # inspect found classes:
            for cls_name, cls in classes:

                if cls_name.startswith("_"):
                    continue

                _inner_classes, inner_functions, inner_methods = self.list_members(cls)

                def full_name(name: str) -> str:
                    return f"{module_name}.{cls_name}.{name}"

                # functions where docstring is None:
                functions_with_missing_docstr.extend(
                    [
                        full_name(name)
                        for name, obj in inner_functions
                        if self.docstring_missing(name, obj)
                    ]
                )

                inconsistent_parameters.extend(
                    full_name(name)
                    for name, func in inner_functions
                    if not (name.startswith("_") or self.docstring_missing(name, func))
                    and self.parameters_inconsistent(
                        parent=f"{module_name}.{cls_name}",
                        call_obj_name=name,
                        call_obj=func,
                    )
                )

                # methods where docstring is None:
                methods_with_missing_docstr.extend(
                    [
                        full_name(name)
                        for name, obj in inner_methods
                        if self.docstring_missing(name, obj)
                    ]
                )

        def lines(s: Iterable[str]) -> str:
            return "\n".join(s)

        if classes_with_missing_docstr:
            log.info(
                "The following classes lack docstrings:\n"
                + lines(classes_with_missing_docstr)
            )

        if functions_with_missing_docstr:
            log.info(
                "The following functions lack docstrings:\n"
                + lines(functions_with_missing_docstr)
            )

        if methods_with_missing_docstr:
            log.info(
                "The following methods lack docstrings:\n"
                + lines(methods_with_missing_docstr)
            )

        if inconsistent_parameters:
            log.info(
                "The following methods have inconsistently described parameters:\n"
                + lines(inconsistent_parameters)
            )

        assert not classes_with_missing_docstr
        assert not functions_with_missing_docstr
        assert not methods_with_missing_docstr
        assert not inconsistent_parameters


def test_docstrings() -> None:
    DocValidator(root_dir="src").validate_docstrings()
