"""Regenerate examples/damaged_part.stl — a sphere with a jagged hole.

    python examples/make_demo.py

The result is deliberately broken (open surface, one boundary loop) so the
inspect/repair workflow can be demonstrated on a realistic scan-like defect.
"""

from __future__ import annotations

import pathlib

import trimesh

OUT = pathlib.Path(__file__).resolve().parent / "damaged_part.stl"


def main() -> None:
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=10.0)
    keep = sphere.triangles_center[:, 2] < 6.0
    damaged = trimesh.Trimesh(sphere.vertices, sphere.faces[keep], process=True)
    damaged.export(str(OUT))
    print(f"wrote {OUT}  watertight={damaged.is_watertight}  "
          f"faces={len(damaged.faces)}")


if __name__ == "__main__":
    main()
