"""
Representations of Python expressions and support for pretty-printed multi-line output.

Useful for generating representations of complex Python objects.

The simplest expressions are `atomic` identifiers and literals, represented by
instances of :class:`.Id` and :class:`.Lit`.
To create an identifier, use one of

.. code-block:: python

    Id.x
    Id("x")

To create identifiers with a leading or trailing underscore, you need to use the
:class:`.Id` constructor as demonstrated in the second variant above.

.. code-block:: python

    Id._x     # will raise exception
    Id.x_     # will raise exception
    Id("_x")  # works
    Id("x_")  # works

To create a literal, use one of

.. code-block:: python

    Lit(3)
    Lit(3.3)
    Lit("text")

See :func:`.make_expression` below for more ways to create literals.

You can use most Python operators to create composite expressions – even using literals
without :class:`.Lit` where the context makes it clear that an expression object is
being constructed, e.g.:

.. code-block:: python

    x, y, z, f, g = Id.x, Id.y, Id.z, Id.f, Id.g
    x + 3   # x is an Expression instance, hence 3 is converted to a Literal object
    3 + x   # this also works if only the second argument is an Expression object
    x == y
    f(3, 5, z)
    g[5]
    g.a

Function :func:`.make_expression` translates most Python objects to useful expressions:

.. code-block:: python

    make_expression(3)
    make_expression(3.3)
    make_expression("text")
    make_expression([3, 5, Id.x])
    make_expression({"a": 3, "b": 5, "c": 6})

If you pass named object to :func:`.make_expression`, e.g., a function or a class,
it will return an identifier with the name of that object.

.. code-block:: python

    make_expression(my_function)
    make_expression(MyClass)

Note that ``a == b`` does not compare two expressions for equality, but creates a
comparison expression.
To compare two expressions, instead use ``a.eq_(b)``, or convert both expressions to
`frozen expressions` using :func:`.freeze`, thus removing their ability to create new
expressions using Python operators: ``freeze(a) == freeze(b)``.

Also note the trailing underscore of method :meth:`~.Expression.eq_`.
By convention, all methods and attributes of expression objects have a trailing
underscore, to distinguish them from the shortcut to generate attribute access
expressions: ``a.eq(b)`` creates a new expression object, rather than comparing
two expressions.

Finally, :class:`.HasExpressionRepr` is a mix-in class that provides a simple way
for any class to produce well-formatted :func:`.repr` string representations
by implementing method :meth:`~.HasExpressionRepr.to_expression` and generating
an :class:`Expression` representation of themselves.

Even class :class:`Expression` subclasses :class:`.HasExpressionRepr`;
:meth:`.Expression.to_expression` returns the expression itself.
"""

from ._expression import *
