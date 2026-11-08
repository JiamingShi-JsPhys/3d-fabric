"""Shared fixtures for the 3d-fabric test suite.

Fixtures are generated at run time (no binary blobs in the repo) so every
test states exactly what geometry it is asserting about.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
import trimesh

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from scripts import engine  # noqa: E402


# ---------------------------------------------------------------------------
# meshes
# ---------------------------------------------------------------------------

@pytest.fixture
def cube():
    """A closed 10 mm cube: watertight, outward normals, 1000 mm^3."""
    return trimesh.creation.box(extents=(10.0, 10.0, 10.0))


@pytest.fixture
def cube_stl(tmp_path, cube):
    path = tmp_path / "cube.stl"
    cube.export(str(path))
    return path


@pytest.fixture
def cube_obj(tmp_path, cube):
    path = tmp_path / "cube.obj"
    cube.export(str(path))
    return path


@pytest.fixture
def open_box_obj(tmp_path, cube):
    """Cube with two adjacent faces deleted -> one 6-vertex boundary loop."""
    keep = cube.faces[2:]
    mesh = trimesh.Trimesh(cube.vertices, keep, process=True)
    path = tmp_path / "open_box.obj"
    mesh.export(str(path))
    return path


@pytest.fixture
def open_tube_stl(tmp_path):
    """Capped cylinder with both caps removed: two 32-vertex boundary loops.

    trimesh's own ``repair.fill_holes`` only closes triangle/quad holes, so
    this fixture is what exercises the fan-fill path.
    """
    solid = trimesh.creation.cylinder(radius=5.0, height=10.0, sections=32)
    side = np.abs(solid.face_normals[:, 2]) < 0.9
    tube = trimesh.Trimesh(solid.vertices, solid.faces[side], process=True)
    path = tmp_path / "open_tube.stl"
    tube.export(str(path))
    return path


@pytest.fixture
def jagged_sphere_stl(tmp_path):
    """Icosphere with the faces above z=6 deleted.

    The resulting boundary ring is jagged, not a clean circle -- exactly what
    a scan or a botched export produces. It is fillable (a flat cap) but not
    perfectly planar.
    """
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=10.0)
    keep = sphere.triangles_center[:, 2] < 6.0
    mesh = trimesh.Trimesh(sphere.vertices, sphere.faces[keep], process=True)
    path = tmp_path / "jagged_sphere.stl"
    mesh.export(str(path))
    return path


@pytest.fixture
def nonmanifold_obj(tmp_path):
    """Three triangles sharing the same edge -- an edge used by 3 faces."""
    vertices = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1]], dtype=float
    )
    faces = np.array([[0, 1, 2], [1, 0, 3], [0, 1, 4]])
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    path = tmp_path / "nonmanifold.obj"
    mesh.export(str(path))
    return path


@pytest.fixture
def inverted_cube_stl(tmp_path):
    """A cube whose faces were flipped: closed, but inside-out."""
    mesh = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    mesh.invert()
    path = tmp_path / "inverted.stl"
    mesh.export(str(path))
    return path


@pytest.fixture
def engine_module():
    return engine
