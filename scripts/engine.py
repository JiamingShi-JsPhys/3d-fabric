#!/usr/bin/env python3
"""3d-fabric engine — inspect, transform, repair and export meshes for 3D printing.

Clean-room design rule
----------------------
Every geometric operation is delegated to ``trimesh`` (MIT).  This module only
orchestrates those APIs, defines a stable JSON report schema, and implements
two trivial bookkeeping helpers that are *not* geometry kernels:

* counting how many faces share an edge (plain ``numpy.unique``), and
* fan-triangulating an already-ordered boundary loop (a for-loop over a
  polygon that ``trimesh`` has just handed us in order).

Nothing here is derived from Cura, PrusaSlicer, Meshmixer, Netfabb or any
other existing tool.  See ``../THIRD_PARTY_LICENSES.txt``.

Public API (imported by ``run.py`` and the test suite)
------------------------------------------------------
    load_mesh(path)                          -> trimesh.Trimesh
    transform(mesh, ...)                     -> trimesh.Trimesh
    analyze(mesh, source=None, fmt=None)     -> dict
    repair(mesh, ...)                        -> (trimesh.Trimesh, dict)
    export_mesh(mesh, path, ...)             -> pathlib.Path

License: MIT. See ../LICENSE.
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:  # trimesh is the only hard requirement
    import trimesh
except ImportError as exc:  # pragma: no cover - exercised only on bare envs
    raise ImportError(
        "3d-fabric requires trimesh (MIT). Install with:\n"
        "    python -m pip install -r requirements.txt"
    ) from exc


__all__ = [
    "MeshError",
    "SUPPORTED_INPUT",
    "SUPPORTED_EXPORT",
    "load_mesh",
    "transform",
    "analyze",
    "repair",
    "export_mesh",
]


SUPPORTED_INPUT = {".stl", ".obj", ".ply", ".glb", ".gltf", ".3mf", ".off"}
SUPPORTED_EXPORT = {"stl", "obj", "ply", "3mf", "glb", "stl_ascii"}

#: STL carries no unit; the report states this assumption explicitly.
UNIT_ASSUMPTION = "mm"

#: Issue codes that ``repair()`` is able to act on.
_REPAIRABLE = {
    "not_watertight",
    "holes",
    "inverted_normals",
    "inverted_body",
    "inconsistent_winding",
    "degenerate_faces",
    "duplicate_vertices",
}


class MeshError(ValueError):
    """The input is unreadable or geometrically unusable."""


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def load_mesh(path: "str | pathlib.Path", *, process: bool = True) -> "trimesh.Trimesh":
    """Load ``.stl`` / ``.obj`` (and PLY/GLB/3MF/OFF) into a single Trimesh.

    ``process=True`` welds coincident vertices, which is mandatory for STL:
    the format stores every triangle's three corners independently, so an
    unwelded STL cube looks like 36 loose vertices and is never watertight.
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise MeshError(f"input not found: {p}")
    if p.suffix.lower() not in SUPPORTED_INPUT:
        raise MeshError(
            f"unsupported format {p.suffix!r}; supported: "
            + ", ".join(sorted(SUPPORTED_INPUT))
        )

    try:
        loaded = trimesh.load(str(p), force="mesh", process=process)
    except Exception as exc:  # trimesh raises a wide variety on bad files
        raise MeshError(f"could not read {p.name}: {exc}") from exc

    if isinstance(loaded, trimesh.Scene):
        # force="mesh" normally concatenates already; this is a belt-and-braces
        # path for scenes whose geometries carry transforms.
        loaded = trimesh.util.concatenate(
            [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        )

    if not isinstance(loaded, trimesh.Trimesh):
        raise MeshError(f"{p.name} does not contain a triangle mesh")
    if len(loaded.faces) == 0:
        raise MeshError(f"{p.name} contains no faces")

    return loaded


# ---------------------------------------------------------------------------
# transforms
# ---------------------------------------------------------------------------

def _as_vec3(value: Any, name: str) -> np.ndarray:
    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size == 1:
        arr = np.repeat(arr, 3)
    if arr.size != 3:
        raise MeshError(f"{name} needs 1 or 3 numbers, got {arr.size}")
    return arr


def transform(
    mesh: "trimesh.Trimesh",
    *,
    scale: Optional[float] = None,
    scale_xyz: Optional[Any] = None,
    translate: Optional[Any] = None,
    rotate_deg: Optional[Any] = None,
    center: bool = False,
    pivot: Optional[Any] = None,
) -> "trimesh.Trimesh":
    """Return a transformed copy of ``mesh``.

    Order of operations is fixed and documented: **scale -> rotate ->
    translate**, then optionally ``center`` (move the bounding-box centre to
    the origin).  Rotation is Euler XYZ in degrees, applied X then Y then Z.
    Scaling happens about ``pivot`` (default: the mesh centroid).
    """
    out = mesh.copy()

    scale_vec = None
    if scale_xyz is not None:
        scale_vec = _as_vec3(scale_xyz, "scale_xyz")
    elif scale is not None:
        if float(scale) <= 0:
            raise MeshError("scale must be > 0")
        scale_vec = np.repeat(float(scale), 3)

    if scale_vec is not None:
        if np.any(scale_vec <= 0):
            raise MeshError("every scale component must be > 0")
        origin = (
            np.asarray(pivot, dtype=float).reshape(3)
            if pivot is not None
            else np.asarray(out.centroid, dtype=float)
        )
        matrix = np.eye(4)
        matrix[:3, :3] = np.diag(scale_vec)
        # trimesh applies transforms to column vectors (v' = M @ v), so
        # "move the pivot to the origin, transform, move it back" is
        # T(origin) @ M @ T(-origin).  The reverse order moves the mesh
        # instead of pinning the pivot.
        matrix = (
            trimesh.transformations.translation_matrix(origin)
            @ matrix
            @ trimesh.transformations.translation_matrix(-origin)
        )
        out.apply_transform(matrix)

    if rotate_deg is not None:
        rx, ry, rz = np.radians(_as_vec3(rotate_deg, "rotate_deg"))
        matrix = trimesh.transformations.euler_matrix(rx, ry, rz, axes="sxyz")
        if pivot is not None:
            origin = np.asarray(pivot, dtype=float).reshape(3)
            matrix = (
                trimesh.transformations.translation_matrix(origin)
                @ matrix
                @ trimesh.transformations.translation_matrix(-origin)
            )
        out.apply_transform(matrix)

    if translate is not None:
        out.apply_translation(_as_vec3(translate, "translate"))

    if center:
        out.apply_translation(-np.asarray(out.bounds, dtype=float).mean(axis=0))

    return out


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------

def _edge_multiplicity(mesh: "trimesh.Trimesh") -> Tuple[np.ndarray, np.ndarray]:
    """Unique undirected edges and how many faces use each one."""
    if len(mesh.faces) == 0:
        return np.zeros((0, 2), dtype=np.int64), np.zeros((0,), dtype=np.int64)
    return np.unique(mesh.edges_sorted, axis=0, return_counts=True)


def _loop_count(vertex_count: int, boundary_edges: np.ndarray) -> int:
    """Number of connected boundary loops.

    Builds a sparse adjacency matrix over the boundary edges only and counts
    connected components that actually own at least one boundary vertex.
    This is graph bookkeeping, not a geometry kernel.
    """
    if len(boundary_edges) == 0:
        return 0
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    rows = boundary_edges[:, 0].astype(np.int64)
    cols = boundary_edges[:, 1].astype(np.int64)
    graph = coo_matrix(
        (np.ones(len(rows), dtype=np.int8), (rows, cols)),
        shape=(vertex_count, vertex_count),
    )
    _, labels = connected_components(graph, directed=False)
    used = np.unique(np.concatenate([rows, cols]))
    return int(len(np.unique(labels[used])))


def _safe_body_count(mesh: "trimesh.Trimesh") -> Optional[int]:
    try:
        return int(mesh.body_count)
    except Exception:  # optional networkx backend missing, or degenerate graph
        return None


#: A direction that is not axis-aligned, so a test ray does not graze an edge
#: or a vertex of a box-shaped shell.
_RAY_DIRECTION = np.array([[0.5773502691896258, 0.5773502691896258, 0.5773502691896258]])


def _point_inside(mesh: "trimesh.Trimesh", point: Any) -> Optional[bool]:
    """Point-in-mesh by ray parity.  ``None`` when the test cannot run.

    ``trimesh.Trimesh.contains`` requires ``rtree``, which is an optional
    dependency this project does not take; ``ray_triangle`` is pure numpy and
    answers the same question for a handful of points.
    """
    try:
        from trimesh.ray import ray_triangle
        triangles = np.asarray(mesh.triangles, dtype=np.float64)
        origin = np.asarray(point, dtype=np.float64).reshape(1, 3)
        _, _, hits = ray_triangle.ray_triangle_id(triangles, origin, _RAY_DIRECTION)
        return bool(len(hits) % 2)
    except Exception:  # pragma: no cover - backend missing or degenerate input
        return None


def _bbox_encloses(inner: "trimesh.Trimesh", outer: "trimesh.Trimesh") -> bool:
    """Fallback containment test when ray parity is unavailable."""
    ib, ob = np.asarray(inner.bounds), np.asarray(outer.bounds)
    return bool(np.all(ib[0] > ob[0]) and np.all(ib[1] < ob[1]))


def _check_bodies(mesh: "trimesh.Trimesh") -> Dict[str, int]:
    """Validate every closed shell on its own, not just the mesh as a whole.

    ``mesh.is_volume`` only proves that the *total* signed volume is positive:
    one small inside-out shell can hide behind a large correct one and the two
    still sum positive, so a global check reports a valid volume for a mesh
    with an inverted part.

    Each closed component is therefore checked separately. A component with a
    negative signed volume is a **cavity** when it sits inside another shell —
    a hollow part is legitimate geometry, and its inner shell is wound
    inwards on purpose — and an **inverted body** when it does not.
    """
    try:
        parts = list(mesh.split(only_watertight=False))
    except Exception:  # degenerate graph; the caller's other checks still run
        return {"closed": 0, "inverted": 0, "cavities": 0}

    closed = [p for p in parts if len(p.faces) and p.is_watertight]
    inverted = 0
    cavities = 0
    for part in closed:
        if float(part.volume) >= 0:
            continue
        centroid = np.asarray(part.centroid, dtype=float).reshape(3)
        inside = False
        for other in closed:
            if other is part:
                continue
            verdict = _point_inside(other, centroid)
            if verdict is None:
                verdict = _bbox_encloses(part, other)
            if verdict:
                inside = True
                break
        if inside:
            cavities += 1
        else:
            inverted += 1
    return {"closed": len(closed), "inverted": inverted, "cavities": cavities}


def analyze(
    mesh: "trimesh.Trimesh",
    *,
    source: Optional[str] = None,
    fmt: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the stable JSON report dict for ``mesh``.

    Report sections: ``geometry`` (measurements), ``topology`` (defects) and
    ``printability`` (verdict + issue list).  Everything is JSON-serialisable.
    """
    uniq_edges, counts = _edge_multiplicity(mesh)
    boundary_edges = uniq_edges[counts == 1]
    nonmanifold_edges = uniq_edges[counts > 2]
    hole_loops = _loop_count(len(mesh.vertices), boundary_edges)

    vertices = np.asarray(mesh.vertices, dtype=float)
    if len(vertices) > 1:
        rounded = np.round(vertices, 8)
        duplicate_vertices = int(len(rounded) - len(np.unique(rounded, axis=0)))
    else:
        duplicate_vertices = 0

    degenerate_faces = int(len(mesh.faces) - len(mesh.nondegenerate_faces()))
    watertight = bool(mesh.is_watertight)
    winding_consistent = bool(mesh.is_winding_consistent)
    signed_volume = float(mesh.volume) if watertight else None
    normals_outward = None if signed_volume is None else signed_volume > 0

    bounds = np.asarray(mesh.bounds, dtype=float)
    extents = bounds[1] - bounds[0]

    body_count = _safe_body_count(mesh)
    bodies = _check_bodies(mesh) if body_count and body_count > 1 else None

    issues: List[Dict[str, Any]] = []

    def issue(code: str, severity: str, message: str, count: Optional[int] = None):
        entry: Dict[str, Any] = {"code": code, "severity": severity, "message": message}
        if count is not None:
            entry["count"] = int(count)
        issues.append(entry)

    if not watertight:
        issue(
            "not_watertight",
            "error",
            "surface is open; a slicer cannot tell inside from outside",
            len(boundary_edges),
        )
    if hole_loops:
        issue("holes", "error", "boundary loops that need filling", hole_loops)
    if len(nonmanifold_edges):
        issue(
            "non_manifold_edges",
            "error",
            "edges shared by 3+ faces or zero-length features",
            len(nonmanifold_edges),
        )
    if not winding_consistent:
        issue(
            "inconsistent_winding",
            "error",
            "adjacent faces disagree about which side is outside; a slicer "
            "cannot reliably tell inside from outside",
        )
    if bodies and bodies["inverted"]:
        issue(
            "inverted_body",
            "error",
            "a closed shell in this mesh is inside-out: its signed volume is "
            "negative and it does not sit inside another shell, so it is not "
            "a cavity",
            bodies["inverted"],
        )
    if normals_outward is False:
        issue(
            "inverted_normals",
            "error",
            "the whole shell is inside-out (negative signed volume)",
        )
    if degenerate_faces:
        issue(
            "degenerate_faces",
            "warning",
            "zero-area triangles; harmless but noisy for slicers",
            degenerate_faces,
        )
    if duplicate_vertices:
        issue(
            "duplicate_vertices",
            "info",
            "coincident vertices that a weld would collapse",
            duplicate_vertices,
        )
    if body_count is not None and body_count > 1:
        issue(
            "multi_body",
            "info",
            "more than one closed shell; print either as separate parts or "
            "joined deliberately",
            body_count,
        )
    if float(extents.min()) <= 0:
        issue("flat_extents", "warning", "the model has zero size along at least one axis")

    errors = [i for i in issues if i["severity"] == "error"]
    error_codes = {i["code"] for i in errors}
    repairable = bool(error_codes) and error_codes.issubset(_REPAIRABLE)
    # ``is_volume`` is trimesh's own "closed, consistently wound, positive
    # volume" test.  It is False for every open mesh, so it only carries
    # information once the surface is watertight — and there it is the
    # backstop that stops a structurally closed but non-solid mesh from
    # being reported as printable.
    solid = (not watertight) or bool(mesh.is_volume)
    if len(mesh.faces) == 0 or float(extents.min()) <= 0:
        verdict = "blocked"
    elif errors or not solid:
        verdict = "needs_repair"
    else:
        verdict = "ready_to_print"

    return {
        "skill": "3d-fabric",
        "action": "inspect",
        "source": str(source) if source else None,
        "format": fmt,
        "assumed_units": UNIT_ASSUMPTION,
        "geometry": {
            "vertex_count": int(len(mesh.vertices)),
            "face_count": int(len(mesh.faces)),
            "unique_edge_count": int(len(uniq_edges)),
            "bounds_min": [round(float(v), 6) for v in bounds[0]],
            "bounds_max": [round(float(v), 6) for v in bounds[1]],
            "extents": [round(float(v), 6) for v in extents],
            "surface_area": round(float(mesh.area), 6),
            "signed_volume": None if signed_volume is None else round(signed_volume, 6),
            "is_volume": bool(mesh.is_volume),
            "body_count": body_count,
            "euler_number": int(mesh.euler_number),
        },
        "topology": {
            "watertight": watertight,
            "winding_consistent": winding_consistent,
            "normals_outward": normals_outward,
            "is_manifold": bool(len(nonmanifold_edges) == 0),
            "boundary_edge_count": int(len(boundary_edges)),
            "hole_loop_count": int(hole_loops),
            "nonmanifold_edge_count": int(len(nonmanifold_edges)),
            "degenerate_face_count": degenerate_faces,
            "duplicate_vertex_count": duplicate_vertices,
        },
        "printability": {
            "verdict": verdict,
            "repairable": repairable,
            "issues": issues,
        },
    }


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------

def _fill_boundary_loops(
    mesh: "trimesh.Trimesh",
    *,
    max_loop_vertices: int = 256,
    planarity_tol: float = 0.05,
) -> Tuple["trimesh.Trimesh", int, List[str]]:
    """Fan-fill every ordered boundary loop that is small and near-planar.

    ``trimesh``'s own ``repair.fill_holes`` only closes single-triangle holes;
    this closes any loop we can order.  The loop comes from
    ``mesh.outline()``; turning an ordered polygon into a triangle fan is
    arithmetic on indices, not a mesh-repair kernel.
    """
    notes: List[str] = []
    try:
        outline = mesh.outline()
        loops = [np.asarray(loop, dtype=float).reshape(-1, 3) for loop in outline.discrete]
    except Exception as exc:
        return mesh, 0, [f"outline unavailable ({exc}); loops left open"]

    if not loops:
        return mesh, 0, notes

    key_to_index = {
        tuple(np.round(v, 9)): i for i, v in enumerate(np.asarray(mesh.vertices, dtype=float))
    }
    extra_vertices: List[np.ndarray] = []
    new_faces: List[List[int]] = []
    filled = 0

    for points in loops:
        if len(points) > 1 and np.allclose(points[0], points[-1]):
            points = points[:-1]
        if len(points) < 3:
            notes.append("skipped a degenerate boundary loop (<3 vertices)")
            continue
        if len(points) > max_loop_vertices:
            notes.append(
                f"skipped a {len(points)}-vertex loop (limit {max_loop_vertices}); "
                "raise --max-hole-loop or repair it in a CAD tool"
            )
            continue

        centre = points.mean(axis=0)
        radius = float(np.linalg.norm(points - centre, axis=1).max())
        if len(points) >= 4 and radius > 0:
            # smallest singular value = spread of the loop along its normal
            s = np.linalg.svd(points - centre, compute_uv=False)
            thickness = float(s[-1]) / np.sqrt(len(points))
            if thickness > planarity_tol * radius:
                notes.append(
                    f"skipped a non-planar loop (thickness {thickness:.4g} > "
                    f"{planarity_tol:g} x radius); fan-filling it would bulge"
                )
                continue

        indices = []
        for point in points:
            key = tuple(np.round(point, 9))
            index = key_to_index.get(key)
            if index is None:  # outline produced a coordinate not in the mesh
                index = len(mesh.vertices) + len(extra_vertices)
                extra_vertices.append(point)
                key_to_index[key] = index
            indices.append(index)

        for i in range(1, len(indices) - 1):
            new_faces.append([indices[0], indices[i], indices[i + 1]])
        filled += 1

    if not new_faces:
        return mesh, 0, notes

    vertices = np.asarray(mesh.vertices, dtype=float)
    if extra_vertices:
        vertices = np.vstack([vertices, np.asarray(extra_vertices, dtype=float)])
    faces = np.vstack([np.asarray(mesh.faces, dtype=np.int64),
                       np.asarray(new_faces, dtype=np.int64)])
    rebuilt = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    notes.append(
        f"fan-filled {filled} boundary loop(s) with {len(new_faces)} flat triangle(s); "
        "a curved surface spanning the hole is not recreated"
    )
    return rebuilt, filled, notes


def repair(
    mesh: "trimesh.Trimesh",
    *,
    fill_holes: bool = True,
    max_loop_vertices: int = 256,
    planarity_tol: float = 0.05,
    max_iterations: int = 3,
    weld: bool = True,
) -> Tuple["trimesh.Trimesh", Dict[str, Any]]:
    """Repair the common print blockers and report exactly what changed.

    Steps, in order: weld vertices, drop degenerate and duplicate faces, drop
    unreferenced vertices, close holes (trimesh's single-face fill, then our
    ordered-loop fan fill, iterated), make winding consistent and orient the
    shell outward.  Nothing is hidden: every step is recorded in
    ``report["steps"]`` with its before/after counts, and the caller gets the
    full before/after analysis.
    """
    work = mesh.copy()
    before = analyze(work, source=None)
    steps: List[Dict[str, Any]] = []
    notes: List[str] = []

    if weld:
        n_before = len(work.vertices)
        work.merge_vertices()
        steps.append({
            "step": "weld_vertices",
            "changed": int(n_before - len(work.vertices)),
        })

    mask = work.nondegenerate_faces()
    dropped = int(len(mask) - int(mask.sum()))
    if dropped:
        work.update_faces(mask)
    steps.append({"step": "drop_degenerate_faces", "changed": dropped})

    mask = work.unique_faces()
    duplicates = int(len(mask) - int(mask.sum()))
    if duplicates:
        work.update_faces(mask)
    steps.append({"step": "drop_duplicate_faces", "changed": duplicates})

    n_before = len(work.vertices)
    work.remove_unreferenced_vertices()
    steps.append({
        "step": "drop_unreferenced_vertices",
        "changed": int(n_before - len(work.vertices)),
    })

    filled_simple = 0
    if fill_holes:
        boundary_before = analyze(work)["topology"]["boundary_edge_count"]
        if boundary_before:
            trimesh.repair.fill_holes(work)
            boundary_after = analyze(work)["topology"]["boundary_edge_count"]
            filled_simple = int(boundary_before - boundary_after)
        steps.append({"step": "fill_single_face_holes", "changed": filled_simple})

        loops_filled = 0
        for _ in range(max_iterations):
            if analyze(work)["topology"]["boundary_edge_count"] == 0:
                break
            work, count, loop_notes = _fill_boundary_loops(
                work,
                max_loop_vertices=max_loop_vertices,
                planarity_tol=planarity_tol,
            )
            notes.extend(loop_notes)
            if count == 0:
                break
            loops_filled += count
        steps.append({"step": "fill_boundary_loops", "changed": loops_filled})

    winding_before = bool(work.is_winding_consistent)
    trimesh.repair.fix_normals(work)
    if work.is_watertight and float(work.volume) < 0:
        trimesh.repair.fix_inversion(work)
    steps.append({
        "step": "fix_normals",
        "changed": int(not winding_before or (work.is_watertight and float(work.volume) < 0)),
    })

    try:
        work.process(validate=True)
    except Exception as exc:  # never let cleanup turn a repair into a crash
        notes.append(f"final validation pass skipped: {exc}")

    after = analyze(work, source=None)
    ok = bool(after["topology"]["watertight"]) and (
        after["geometry"]["signed_volume"] is None
        or after["geometry"]["signed_volume"] > 0
    )
    report = {
        "skill": "3d-fabric",
        "action": "repair",
        "before": before,
        "after": after,
        "steps": steps,
        "notes": notes,
        "watertight_after": bool(after["topology"]["watertight"]),
        "success": ok,
    }
    return work, report


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def export_mesh(
    mesh: "trimesh.Trimesh",
    path: "str | pathlib.Path",
    *,
    ascii_stl: bool = False,
    file_type: Optional[str] = None,
) -> pathlib.Path:
    """Write ``mesh`` to ``path``; returns the resolved output path.

    STL defaults to binary (the standard for slicers); ``ascii_stl=True``
    selects the ASCII variant.  OBJ, PLY, 3MF and GLB are exported untouched.
    """
    out = pathlib.Path(path)
    suffix = out.suffix.lower().lstrip(".")
    kind = (file_type or suffix or "stl").lower()
    if kind == "stl" and ascii_stl:
        kind = "stl_ascii"
    if kind not in SUPPORTED_EXPORT:
        raise MeshError(
            f"unsupported export format {kind!r}; supported: "
            + ", ".join(sorted(SUPPORTED_EXPORT))
        )

    if not mesh.is_watertight:
        # Not fatal: a slicer will usually still open it, but never pretend.
        pass

    try:
        payload = mesh.export(file_type=kind)
    except Exception as exc:
        raise MeshError(f"export to {kind} failed: {exc}") from exc

    out.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        out.write_text(payload, encoding="utf-8")
    elif isinstance(payload, (bytes, bytearray)):
        out.write_bytes(bytes(payload))
    else:  # trimesh returns a dict for archive-style exports (e.g. some 3MF paths)
        raise MeshError(
            f"unexpected payload type {type(payload).__name__} from trimesh for {kind}"
        )
    return out
