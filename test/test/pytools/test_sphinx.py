import logging
from typing import Dict, Generic, Type, TypeVar

from pytools.sphinx import ResolveGenericClassParameters
from pytools.viz import Drawer
from pytools.viz.distribution import ECDFDrawer
from pytools.viz.distribution.base import ECDFStyle

log = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


class A(Generic[T, U]):
    def f(self, x: Type[T]) -> U:
        pass


class B(A[U, int], Generic[U, V]):
    pass


class C(B[str, T]):
    pass


def test_resolve_generic_class_parameters():
    resolve_generic_class_parameters = ResolveGenericClassParameters()

    resolve_generic_class_parameters.process(app=None, obj=Drawer, bound_method=False)

    resolve_generic_class_parameters.process(
        app=None, obj=ECDFDrawer, bound_method=False
    )

    resolve_generic_class_parameters.process(
        app=None, obj=ECDFDrawer.get_named_styles, bound_method=True
    )
    # noinspection PyUnresolvedReferences
    assert ECDFDrawer.get_named_styles.__annotations__ == {
        "return": Dict[str, Type[ECDFStyle]]
    }

    resolve_generic_class_parameters.process(app=None, obj=A, bound_method=False)
    resolve_generic_class_parameters.process(app=None, obj=A.f, bound_method=False)
    assert A.f.__annotations__ == {"x": Type[T], "return": U}

    resolve_generic_class_parameters.process(app=None, obj=B, bound_method=False)
    resolve_generic_class_parameters.process(app=None, obj=B.f, bound_method=False)
    assert B.f.__annotations__ == {"x": Type[U], "return": int}

    resolve_generic_class_parameters.process(app=None, obj=C, bound_method=False)
    resolve_generic_class_parameters.process(app=None, obj=C.f, bound_method=False)
    assert C.f.__annotations__ == {"x": Type[str], "return": int}
