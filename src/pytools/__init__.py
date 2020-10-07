"""
A collection of tools used across Gamma's open-source libraries.
"""

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
