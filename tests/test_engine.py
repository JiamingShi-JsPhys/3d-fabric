"""Engine tests — geometry, topology detection, repair and export.

Every assertion is about a fixture whose exact geometry is known, so the
numbers in the test are meaningful rather than "whatever trimesh returned".
"""

from __future__ import annotations

import json

import numpy as np
import pytest
import trimesh

from scripts import engine  # pyright: ignore[reportAttributeAccessIssue]


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def test_load_stl_welds_vertices(cube_stl):
    mesh = engine.load_mesh(cube_stl)
    assert len(mesh.vertices) == 8, "STL corners must be welded into 8 vertices"
    assert len(mesh.faces) == 12
    assert mesh.is_watertight


def test_load_obj(cube_obj):
    mesh = engine.load_mesh(cube_obj)
    assert len(mesh.faces) == 12
    assert mesh.is_watertight


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(engine.MeshError, match="not found"):
        engine.load_mesh(tmp_path / "nope.stl")


def test_load_unsupported_extension_raises(tmp_path):
    bad = tmp_path / "model.txt"
    bad.write_text("not a mesh", encoding="utf-8")
    with pytest.raises(engine.MeshError, match="unsupported format"):
        engine.load_mesh(bad)


# ---------------------------------------------------------------------------
# transforms
# ---------------------------------------------------------------------------

def test_scale_is_applied_about_centroid(cube):
    scaled = engine.transform(cube, scale=2.0)
    assert np.allclose(scaled.extents, [20, 20, 20], atol=1e-6)
    assert np.allclose(scaled.centroid, cube.centroid, atol=1e-6)
    assert scaled.volume == pytest.approx(8000.0, rel=1e-6)


def test_per_axis_scale(cube):
    scaled = engine.transform(cube, scale_xyz=[1, 2, 3])
    assert np.allclose(scaled.extents, [10, 20, 30], atol=1e-6)


def test_translate(cube):
    moved = engine.transform(cube, translate=[100, -5, 0.5])
    assert np.allclose(moved.centroid, cube.centroid + [100, -5, 0.5], atol=1e-6)


def test_rotate_swap_xy(cube):
    rotated = engine.transform(cube, rotate_deg=[0, 0, 90])
    # a cube is symmetric, so check a non-symmetric model instead
    bar = trimesh.creation.box(extents=(10, 2, 2))
    turned = engine.transform(bar, rotate_deg=[0, 0, 90])
    assert np.allclose(turned.extents, [2, 10, 2], atol=1e-6)
    assert np.allclose(rotated.extents, [10, 10, 10], atol=1e-6)


def test_center_moves_bounds_to_origin(cube):
    shifted = engine.transform(cube, translate=[50, 50, 50], center=True)
    centre = shifted.bounds.mean(axis=0)
    assert np.allclose(centre, [0, 0, 0], atol=1e-6)


def test_transform_does_not_mutate_input(cube):
    before = cube.copy()
    engine.transform(cube, scale=3.0, translate=[9, 9, 9])
    assert np.allclose(cube.vertices, before.vertices)


def test_negative_scale_is_refused(cube):
    with pytest.raises(engine.MeshError, match="scale"):
        engine.transform(cube, scale=-1.0)


# ---------------------------------------------------------------------------
# inspection
# ---------------------------------------------------------------------------

def test_inspect_clean_cube(cube):
    report = engine.analyze(cube, source="cube.stl", fmt="stl")
    topo = report["topology"]
    geo = report["geometry"]

    assert topo["watertight"] is True
    assert topo["winding_consistent"] is True
    assert topo["normals_outward"] is True
    assert topo["is_manifold"] is True
    assert topo["boundary_edge_count"] == 0
    assert topo["hole_loop_count"] == 0
    assert topo["nonmanifold_edge_count"] == 0
    assert geo["vertex_count"] == 8
    assert geo["face_count"] == 12
    assert geo["signed_volume"] == pytest.approx(1000.0)
    assert geo["euler_number"] == 2
    assert report["printability"]["verdict"] == "ready_to_print"
    assert report["printability"]["issues"] == []


def test_inspect_finds_open_surface(open_box_obj):
    report = engine.analyze(engine.load_mesh(open_box_obj))
    topo = report["topology"]
    assert topo["watertight"] is False
    # the fixture removes one whole side of the cube (2 triangles) -> 4 edges
    assert topo["boundary_edge_count"] == 4
    assert topo["hole_loop_count"] == 1
    codes = {i["code"] for i in report["printability"]["issues"]}
    assert {"not_watertight", "holes"} <= codes
    assert report["printability"]["verdict"] == "needs_repair"
    assert report["printability"]["repairable"] is True


def test_inspect_finds_nonmanifold_edge(nonmanifold_obj):
    report = engine.analyze(engine.load_mesh(nonmanifold_obj))
    topo = report["topology"]
    assert topo["nonmanifold_edge_count"] == 1
    assert topo["is_manifold"] is False
    codes = {i["code"] for i in report["printability"]["issues"]}
    assert "non_manifold_edges" in codes
    # our repair cannot split a non-manifold edge, and must say so
    assert report["printability"]["repairable"] is False


def test_inspect_detects_inverted_normals(inverted_cube_stl):
    report = engine.analyze(engine.load_mesh(inverted_cube_stl))
    topo = report["topology"]
    assert topo["watertight"] is True
    assert topo["normals_outward"] is False
    assert report["geometry"]["signed_volume"] < 0
    codes = {i["code"] for i in report["printability"]["issues"]}
    assert "inverted_normals" in codes


def test_inspect_counts_two_hole_loops(open_tube_stl):
    report = engine.analyze(engine.load_mesh(open_tube_stl))
    assert report["topology"]["hole_loop_count"] == 2
    assert report["topology"]["boundary_edge_count"] == 64


def test_report_is_json_serialisable(cube):
    report = engine.analyze(cube, source="cube.stl", fmt="stl")
    text = json.dumps(report)
    assert json.loads(text)["geometry"]["face_count"] == 12


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------

def test_repair_fills_large_holes(open_tube_stl):
    mesh = engine.load_mesh(open_tube_stl)
    repaired, report = engine.repair(mesh)

    assert report["success"] is True
    assert report["watertight_after"] is True
    assert report["after"]["topology"]["hole_loop_count"] == 0
    # 32-gon caps are slightly smaller than true circles: area = n/2 r^2 sin(2pi/n)
    expected = 0.5 * 32 * 25.0 * np.sin(2 * np.pi / 32) * 10.0
    assert repaired.volume == pytest.approx(expected, rel=1e-3)
    assert repaired.is_winding_consistent


def test_repair_closes_small_hole(open_box_obj):
    repaired, report = engine.repair(engine.load_mesh(open_box_obj))
    assert report["success"] is True
    assert repaired.is_watertight
    assert repaired.volume == pytest.approx(1000.0, rel=1e-6)


def test_repair_flips_inverted_shell(inverted_cube_stl):
    repaired, report = engine.repair(engine.load_mesh(inverted_cube_stl))
    assert report["success"] is True
    assert repaired.volume > 0
    assert report["after"]["topology"]["normals_outward"] is True


def test_repair_can_skip_hole_filling(open_tube_stl):
    mesh = engine.load_mesh(open_tube_stl)
    _, report = engine.repair(mesh, fill_holes=False)
    assert report["watertight_after"] is False
    assert report["success"] is False


def test_repair_fills_a_jagged_scan_like_hole(jagged_sphere_stl):
    """A slightly non-planar boundary ring must still be filled by default."""
    repaired, report = engine.repair(engine.load_mesh(jagged_sphere_stl))
    assert report["success"] is True
    assert repaired.is_watertight
    assert repaired.volume > 0
    assert any("fan-filled" in note for note in report["notes"])


def test_repair_refuses_a_loop_beyond_the_planarity_tolerance(jagged_sphere_stl):
    """With a tight tolerance the guard must refuse instead of bulging."""
    _, report = engine.repair(
        engine.load_mesh(jagged_sphere_stl), planarity_tol=1e-4
    )
    assert report["watertight_after"] is False
    assert any("non-planar" in note for note in report["notes"])


def test_repair_reports_every_step(open_box_obj):
    _, report = engine.repair(engine.load_mesh(open_box_obj))
    names = [s["step"] for s in report["steps"]]
    assert names == [
        "weld_vertices",
        "drop_degenerate_faces",
        "drop_duplicate_faces",
        "drop_unreferenced_vertices",
        "fill_single_face_holes",
        "fill_boundary_loops",
        "fix_normals",
    ]
    for step in report["steps"]:
        assert isinstance(step["changed"], int)


def test_repair_is_honest_about_nonmanifold(nonmanifold_obj):
    _, report = engine.repair(engine.load_mesh(nonmanifold_obj))
    # cannot be fixed by welding/filling; must not claim success
    assert report["success"] is False
    assert report["after"]["topology"]["nonmanifold_edge_count"] == 1


def test_repair_preserves_a_clean_mesh(cube):
    repaired, report = engine.repair(cube)
    assert report["success"] is True
    assert repaired.volume == pytest.approx(1000.0, rel=1e-6)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def test_export_binary_stl_roundtrip(tmp_path, cube):
    out = engine.export_mesh(cube, tmp_path / "out.stl")
    back = trimesh.load(str(out), force="mesh")
    assert isinstance(back, trimesh.Trimesh)
    assert len(back.faces) == 12
    assert back.is_watertight
    assert out.read_bytes()[:5] != b"solid", "binary STL must not start with 'solid'"


def test_export_ascii_stl_roundtrip(tmp_path, cube):
    out = engine.export_mesh(cube, tmp_path / "out.stl", ascii_stl=True)
    assert out.read_bytes().lstrip().startswith(b"solid")
    back = trimesh.load(str(out), force="mesh")
    assert isinstance(back, trimesh.Trimesh)
    assert len(back.faces) == 12


def test_export_is_readable_by_numpy_stl(tmp_path, cube):
    """Cross-check with an independent BSD-licensed STL reader.

    Proves the exported file is a standard STL, not merely something trimesh
    can read back.
    """
    stl = pytest.importorskip("stl")
    out = engine.export_mesh(cube, tmp_path / "cross.stl")
    mesh = stl.mesh.Mesh.from_file(str(out))
    assert len(mesh.vectors) == 12
    assert mesh.vectors.shape == (12, 3, 3)


def test_export_obj_and_3mf(tmp_path, cube):
    obj = engine.export_mesh(cube, tmp_path / "out.obj")
    assert obj.read_text(encoding="utf-8").count("\nf ") >= 12
    threemf = engine.export_mesh(cube, tmp_path / "out.3mf")
    assert threemf.stat().st_size > 0


def test_export_rejects_unknown_format(tmp_path, cube):
    with pytest.raises(engine.MeshError, match="unsupported export format"):
        engine.export_mesh(cube, tmp_path / "out.xyz")


def test_export_creates_parent_directory(tmp_path, cube):
    out = engine.export_mesh(cube, tmp_path / "deep" / "nested" / "out.stl")
    assert out.is_file()
