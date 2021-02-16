"""
Composite expressions.

A composite expressions combines subexpressions to form a new, combines expression.

Composite expressions comprise

- operations: e.g., ``-<expression>``, ``<expression 1> - <expression 2>``
- tuple, list, set, dictionary literals
- call expressions: ``<expression 1>(<expression 2>])``
- indexing expressions: ``<expression 1>[<expression 2>]``
- attribute access: ``<expression 1>.<attribute name>``
- lambda expressions: ``lambda [x, y, …]: <expression>``
"""

from ._composite import *
