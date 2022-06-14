#!/usr/bin/env python3
"""
Make sphinx documentation using the makefile in pytools
"""

import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "base")
    )

    from make_base import make

    make()
