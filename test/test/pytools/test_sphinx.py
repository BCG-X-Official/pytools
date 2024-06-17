import logging
import typing
from collections.abc import Iterable
from typing import Any, Generic, TypeVar

from pytools.viz import Drawer
from pytools.viz.distribution import ECDFDrawer
from pytools.viz.distribution.base import ECDFStyle

log = logging.getLogger(__name__)

S = TypeVar("S")
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


class A(Generic[T, U]):
    def f(self: S, x: type[T]) -> U:  # type: ignore[empty-body]
        pass

    def g(self: S) -> S | None:
        pass

    @classmethod
    def h(cls: type[S]) -> S:
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

    def _set_current_class(cls: type[Any]) -> None:
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

    assert ECDFDrawer.get_style_classes.__annotations__ == {
        "return": Iterable[type[ECDFStyle]]
    }

    _set_current_class(A)

    resolve_type_variables.process(app=sphinx, obj=A, bound_method=False)
    resolve_type_variables.process(app=sphinx, obj=A.f, bound_method=False)

    type_a = type[A]  # type: ignore[type-arg]
    type_b = type[B]  # type: ignore[type-arg]
    type_t = type[T]
    type_u = type[U]
    type_str = type[str]

    assert A.f.__annotations__ == {"self": A, "x": type_t, "return": U}
    resolve_type_variables.process(app=sphinx, obj=A.g, bound_method=False)
    assert A.g.__annotations__ == {"self": A, "return": typing.Optional[A]}

    resolve_type_variables.process(app=sphinx, obj=A.h, bound_method=False)
    assert A.h.__annotations__ == {"cls": type_a, "return": A}

    _set_current_class(B)

    resolve_type_variables.process(app=sphinx, obj=B, bound_method=False)
    resolve_type_variables.process(app=sphinx, obj=B.f, bound_method=False)
    assert B.f is A.f
    assert A.f.__annotations__ == {"self": B, "x": type_u, "return": int}
    resolve_type_variables.process(app=sphinx, obj=B.g, bound_method=False)
    assert B.g is A.g
    assert A.g.__annotations__ == {"self": B, "return": typing.Optional[B]}
    resolve_type_variables.process(app=sphinx, obj=B.h, bound_method=False)
    assert B.h is not A.h
    assert B.h.__annotations__ == {"cls": type_b, "return": B}

    _set_current_class(C)

    resolve_type_variables.process(app=sphinx, obj=C, bound_method=False)
    resolve_type_variables.process(app=sphinx, obj=C.f, bound_method=False)
    assert C.f is A.f
    assert A.f.__annotations__ == {"self": C, "x": type_str, "return": int}
