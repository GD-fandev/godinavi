"""Compatibility exports for the V2 package format.

The shared implementation was promoted to :mod:`monster_pak` in the 1.5
development line.  V2 components keep this module name so older manifests and
tests can continue to use the established update contract.
"""

from monster_pak import *  # noqa: F401,F403
