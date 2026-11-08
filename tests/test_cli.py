"""CLI tests — the contract a pipeline or a human actually calls.

Runs ``run.py`` as a subprocess exactly the way the docs advertise, and checks
exit codes, the single-line gate JSON, and the files it writes.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest
import trimesh

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = PLUGIN_ROOT / "run.py"


def run_cli(*args, cwd=None):
    proc = subprocess.run(
        [sys.executable, str(RUN), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd or PLUGIN_ROOT),
    )
    return proc


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

def test_inspect_clean_mesh_exits_zero(cube_stl):
    proc = run_cli("--action", "inspect", "--input", cube_stl, "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "PASS"
    assert payload["data"]["inspection"]["printability"]["verdict"] == "ready_to_print"
    assert payload["data"]["inspection"]["geometry"]["face_count"] == 12
    assert payload["evidence_level"] == "EMPIRICAL"


def test_inspect_broken_mesh_exits_two(open_box_obj):
    proc = run_cli("--action", "inspect", "--input", open_box_obj, "--json")
    assert proc.returncode == 2, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "UNVERIFIED"
    assert payload["data"]["inspection"]["topology"]["watertight"] is False


def test_inspect_human_output_mentions_verdict(cube_stl):
    proc = run_cli("--action", "inspect", "--input", cube_stl)
    assert proc.returncode == 0
    assert "3d-fabric" in proc.stdout
    assert "ready_to_print" in proc.stdout
    assert "watertight[OK]" in proc.stdout


def test_inspect_missing_file_exits_two(tmp_path):
    proc = run_cli("--action", "inspect", "--input", tmp_path / "ghost.stl")
    assert proc.returncode == 2
    assert "not found" in (proc.stdout + proc.stderr)


def test_inspect_writes_gate_under_root(cube_stl, tmp_path):
    root = tmp_path / "ws"
    proc = run_cli("--action", "inspect", "--input", cube_stl, "--root", root, "--json")
    assert proc.returncode == 0, proc.stderr
    gates = list((root / "process" / "gates").glob("3d-fabric_*.json"))
    assert len(gates) == 1
    gate = json.loads(gates[0].read_text(encoding="utf-8"))
    assert gate["skill"] == "3d-fabric"
    assert gate["status"] == "PASS"
    assert gate["timestamp"]


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------

def test_repair_writes_a_watertight_file(open_tube_stl, tmp_path):
    out = tmp_path / "fixed.stl"
    proc = run_cli("--action", "repair", "--input", open_tube_stl,
                   "--output", out, "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "PASS"
    assert out.is_file()

    back = trimesh.load(str(out), force="mesh")
    assert isinstance(back, trimesh.Trimesh)
    assert back.is_watertight
    assert back.volume > 0


def test_repair_default_output_name(open_box_obj):
    proc = run_cli("--action", "repair", "--input", open_box_obj, "--json")
    assert proc.returncode == 0, proc.stderr
    expected = open_box_obj.with_name(open_box_obj.stem + "_repaired.obj")
    assert expected.is_file(), f"expected {expected}"
    expected.unlink()


def test_repair_with_root_uses_process_dirs(open_box_obj, tmp_path):
    root = tmp_path / "ws"
    proc = run_cli("--action", "repair", "--input", open_box_obj,
                   "--root", root, "--json")
    assert proc.returncode == 0, proc.stderr
    assert list((root / "process" / "models").glob("open_box_repaired.*"))
    assert list((root / "process" / "gates").glob("3d-fabric_*.json"))


def test_repair_applies_transform_before_export(cube_stl, tmp_path):
    out = tmp_path / "scaled.stl"
    proc = run_cli("--action", "repair", "--input", cube_stl, "--output", out,
                   "--scale", "2", "--translate", "10,0,0", "--json")
    assert proc.returncode == 0, proc.stderr
    back = trimesh.load(str(out), force="mesh")
    assert isinstance(back, trimesh.Trimesh)
    assert list(back.extents) == pytest.approx([20, 20, 20], abs=1e-3)
    assert back.bounds[0][0] == pytest.approx(0.0, abs=1e-3)


def test_repair_ascii_flag(open_box_obj, tmp_path):
    out = tmp_path / "ascii.stl"
    proc = run_cli("--action", "repair", "--input", open_box_obj,
                   "--output", out, "--ascii", "--json")
    assert proc.returncode == 0, proc.stderr
    assert out.read_bytes().lstrip().startswith(b"solid")


def test_repair_reports_remaining_nonmanifold(nonmanifold_obj, tmp_path):
    out = tmp_path / "nm.obj"
    proc = run_cli("--action", "repair", "--input", nonmanifold_obj,
                   "--output", out, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "FAIL"
    assert payload["data"]["after"]["topology"]["nonmanifold_edge_count"] == 1


def test_repair_no_fill_holes(open_box_obj, tmp_path):
    out = tmp_path / "open.stl"
    proc = run_cli("--action", "repair", "--input", open_box_obj, "--output", out,
                   "--no-fill-holes", "--json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "FAIL"


def test_bad_arguments_exit_nonzero():
    proc = run_cli("--action", "slice", "--input", "x.stl")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr
