"""3d-fabric internals.

``engine``      — trimesh-backed geometry: load, transform, analyze, repair, export.
``solidcraft``  — the local SolidCraft CLI bridge: probe, run, verify output.
"""

from . import engine, solidcraft

__all__ = ["engine", "solidcraft"]
