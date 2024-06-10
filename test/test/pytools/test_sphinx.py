import logging
from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar

from pytools.viz import Drawer
from pytools.viz.distribution import ECDFDrawer
from pytools.viz.distribution.base import ECDFStyle

log = logging.getLogger(__name__)

S = TypeVar("S")
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


class A(Generic[T, U]):
    def f(self: S, x: Type[T]) -> U:  # type: ignore[empty-body]
        pass

    def g(self: S) -> Optional[S]:
        pass

    @classmethod
    def h(cls: Type[S]) -> S:
        return cls()


class B(A[U, int], Generic[U, V]):
    pass


class C(B[str, T]):
    pass


# noinspection PyUnresolvedReferences
def test_resolve_generic_class_parameters() -> None:
    from pytools.sphinx.util import ResolveTypeVariables, TrackCurrentClass

    sphinx = type("Sphinx", (object,), {})()

    track_current_class = TrackCurrentClass()
    resolve_type_variables = ResolveTypeVariables()

    def _set_current_class(cls: Type[Any]) -> None:
        track_current_class.process(
            app=sphinx,
            what="class",
            name=cls.__name__,
            obj=cls,
            options={},
            signature="",
            return_annotation="",
        )

    _set_current_class(ECDFDrawer)

    resolve_type_variables.process(app=sphinx, obj=Drawer, bound_method=False)

    resolve_type_variables.process(app=sphinx, obj=ECDFDrawer, bound_method=False)

    resolve_type_variables.process(
        app=sphinx, obj=ECDFDrawer.get_named_styles, bound_method=True
    )

    assert ECDFDrawer.get_named_styles.__annotations__ == {
        "return": Dict[str, Callable[..., ECDFStyle]]
    }

    _set_current_class(A)

    resolve_type_variables.process(app=sphinx, obj=A, bound_method=False)
    resolve_type_variables.process(app=sphinx, obj=A.f, bound_method=False)
    assert A.f.__annotations__ == {"self": A, "x": Type[T], "return": U}
    resolve_type_variables.process(app=sphinx, obj=A.g, bound_method=False)
    assert A.g.__annotations__ == {"self": A, "return": Optional[A]}

    resolve_type_variables.process(app=sphinx, obj=A.h, bound_method=False)
    assert A.h.__annotations__ == {"cls": Type[A], "return": A}

    _set_current_class(B)

    resolve_type_variables.process(app=sphinx, obj=B, bound_method=False)
    resolve_type_variables.process(app=sphinx, obj=B.f, bound_method=False)
    assert B.f is A.f
    assert A.f.__annotations__ == {"self": B, "x": Type[U], "return": int}
    resolve_type_variables.process(app=sphinx, obj=B.g, bound_method=False)
    assert B.g is A.g
    assert A.g.__annotations__ == {"self": B, "return": Optional[B]}
    resolve_type_variables.process(app=sphinx, obj=B.h, bound_method=False)
    assert B.h is not A.h
    assert B.h.__annotations__ == {"cls": Type[B], "return": B}

    _set_current_class(C)

    resolve_type_variables.process(app=sphinx, obj=C, bound_method=False)
    resolve_type_variables.process(app=sphinx, obj=C.f, bound_method=False)
    assert C.f is A.f
    assert A.f.__annotations__ == {"self": C, "x": Type[str], "return": int}
