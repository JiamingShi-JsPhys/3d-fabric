"""Action tests for measure / snapshot / script, and model --in.

These are the actions that make 3d-fabric a complete front end for a design
someone already has, not only for one built from scratch.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
STUB = pathlib.Path(__file__).resolve().parent / "stub_solidcraft.py"

_spec = importlib.util.spec_from_file_location("fabric_cli_actions", PLUGIN_ROOT / "run.py")
assert _spec is not None and _spec.loader is not None
fabric = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fabric)


def _last_json(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


@pytest.fixture
def design(tmp_path):
    path = tmp_path / "part.sc"
    path.write_text("stub design\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# measure
# ---------------------------------------------------------------------------

def test_measure_reports_totals(design, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    code = fabric.main(["--action", "measure", "--input", str(design),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 0
    gate = _last_json(capsys)
    assert gate["status"] == "PASS"
    totals = gate["data"]["totals"]
    assert totals["body_count"] == 1
    assert totals["volume_mm3"] == 1000.0
    assert totals["mass_g"] == 1.29
    assert totals["all_closed"] is True
    assert gate["data"]["measurements"]["bodies"][0]["face_types"] == {"plane": 6}


def test_measure_open_body_is_unverified(design, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "open")
    code = fabric.main(["--action", "measure", "--input", str(design),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 2
    gate = _last_json(capsys)
    assert gate["status"] == "UNVERIFIED"
    assert gate["data"]["totals"]["all_closed"] is False


def test_measure_reports_cli_failure(design, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "fail")
    code = fabric.main(["--action", "measure", "--input", str(design),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 1
    assert _last_json(capsys)["status"] == "FAIL"


def test_measure_needs_an_existing_design(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    code = fabric.main(["--action", "measure", "--input", str(tmp_path / "nope.sc"),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 2
    assert "design not found" in _last_json(capsys)["reason"]


def test_measure_human_output_mentions_mass(design, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    code = fabric.main(["--action", "measure", "--input", str(design),
                        "--solidcraft", str(STUB)])
    assert code == 0
    out = capsys.readouterr().out
    assert "3d-fabric · measure" in out
    assert "77" not in out  # this stub reports 1.29 g, not the real bracket
    assert "1.290 g" in out
    assert "closed[OK]" in out


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def test_snapshot_writes_a_png(design, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    out = tmp_path / "shot.png"
    code = fabric.main(["--action", "snapshot", "--input", str(design),
                        "--output", str(out), "--view", "iso",
                        "--width", "640", "--height", "480",
                        "--solidcraft", str(STUB), "--json"])
    assert code == 0
    assert out.read_bytes()[:4] == b"\x89PNG"
    gate = _last_json(capsys)
    assert gate["status"] == "PASS"
    assert gate["data"]["image"] == str(out)
    assert gate["data"]["info"]["width"] == 640


def test_snapshot_failure_is_reported(design, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "fail")
    code = fabric.main(["--action", "snapshot", "--input", str(design),
                        "--output", str(tmp_path / "s.png"),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 1
    assert _last_json(capsys)["status"] == "FAIL"


def test_snapshot_defaults_next_to_the_design(design, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    code = fabric.main(["--action", "snapshot", "--input", str(design),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 0
    assert (design.parent / "part.png").is_file()


# ---------------------------------------------------------------------------
# script
# ---------------------------------------------------------------------------

def test_script_extracts_commands(design, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    out = tmp_path / "build.json"
    code = fabric.main(["--action", "script", "--input", str(design),
                        "--output", str(out), "--solidcraft", str(STUB), "--json"])
    assert code == 0
    gate = _last_json(capsys)
    assert gate["status"] == "PASS"
    assert gate["data"]["step_count"] == 2
    assert gate["data"]["script"] == str(out)

    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["commands"][0]["command"] == "parameters.add"
    assert any("replay" in note for note in gate["data"]["notes"])


def test_script_failure_is_reported(design, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "fail")
    code = fabric.main(["--action", "script", "--input", str(design),
                        "--output", str(tmp_path / "b.json"),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 1


# ---------------------------------------------------------------------------
# model --in
# ---------------------------------------------------------------------------

def test_model_in_passes_the_design_to_solidcraft(tmp_path, design, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    argv_out = tmp_path / "argv.json"
    monkeypatch.setenv("STUB_ARGV_OUT", str(argv_out))

    patch = tmp_path / "patch.json"
    patch.write_text(json.dumps({"commands": [
        {"command": "parameters.change", "params": {"name": "L", "expression": "150 mm"}}
    ]}), encoding="utf-8")

    code = fabric.main(["--action", "model", "--script", str(patch),
                        "--in", str(design), "--output", str(tmp_path / "out.stl"),
                        "--solidcraft", str(STUB), "--no-save-design", "--json"])
    assert code == 0, capsys.readouterr().out

    argv = json.loads(argv_out.read_text(encoding="utf-8"))
    assert "--in" in argv
    assert argv[argv.index("--in") + 1] == str(design)
    gate = _last_json(capsys)
    assert any("existing design" in note for note in gate["data"]["notes"])


def test_model_in_rejects_a_missing_design(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    patch = tmp_path / "patch.json"
    patch.write_text('{"commands":[{"command":"solid.box","params":{"length":10}}]}',
                     encoding="utf-8")
    code = fabric.main(["--action", "model", "--script", str(patch),
                        "--in", str(tmp_path / "ghost.sc"),
                        "--output", str(tmp_path / "o.stl"),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 2
    assert "design not found" in _last_json(capsys)["reason"]
