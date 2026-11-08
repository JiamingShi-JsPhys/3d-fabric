"""Model action tests — the full natural-language → SolidCraft → STL chain.

The runner is imported in-process so the stub CLI's behaviour can be switched
with an environment variable, and ``probe`` can be monkeypatched for the
"SolidCraft is missing" path.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest
import trimesh

from scripts import solidcraft as sc  # pyright: ignore[reportAttributeAccessIssue]

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
STUB = pathlib.Path(__file__).resolve().parent / "stub_solidcraft.py"

_spec = importlib.util.spec_from_file_location("fabric_cli", PLUGIN_ROOT / "run.py")
assert _spec is not None and _spec.loader is not None
fabric = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fabric)


def _last_json(capsys):
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])


@pytest.fixture
def script_file(tmp_path):
    path = tmp_path / "box.json"
    path.write_text(json.dumps({"commands": [
        {"command": "solid.box", "params": {"length": 10, "width": 10, "height": 10}}
    ]}), encoding="utf-8")
    return path


@pytest.fixture
def requirement_file(tmp_path):
    path = tmp_path / "req.json"
    path.write_text(json.dumps({
        "prompt": "a 10mm cube",
        "commands": [
            {"command": "solid.box",
             "params": {"length": 10, "width": 10, "height": 10}}
        ],
        "output": "cube.stl",
        "quality": "fine",
    }), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# success path
# ---------------------------------------------------------------------------

def test_model_builds_and_inspects(tmp_path, script_file, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    out = tmp_path / "part.stl"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--solidcraft", str(STUB),
                        "--no-save-design", "--json"])
    assert code == 0
    gate = _last_json(capsys)

    assert gate["status"] == "PASS"
    assert out.is_file()
    analysis = gate["data"]["inspection"]
    assert analysis["topology"]["watertight"] is True
    assert analysis["geometry"]["face_count"] == 12
    assert analysis["printability"]["verdict"] == "ready_to_print"
    assert gate["data"]["probe"]["installed"] is True


def test_model_from_requirement_json_materialises_script(tmp_path, requirement_file,
                                                         monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    code = fabric.main(["--action", "model", "--input", str(requirement_file),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 0
    gate = _last_json(capsys)
    assert gate["status"] == "PASS"
    assert (tmp_path / "cube.stl").is_file()
    assert (tmp_path / "cube.solidcraft.json").is_file()

    # fine quality is injected as an export command with an absolute path
    script = json.loads((tmp_path / "cube.solidcraft.json").read_text(encoding="utf-8"))
    export = [c for c in script["commands"] if c["command"].startswith("file.export")]
    assert export and export[0]["params"]["quality"] == "fine"
    assert pathlib.Path(export[0]["params"]["path"]).is_absolute()

    # ...and the prompt survives into the report
    assert gate["data"]["prompt"] == "a 10mm cube"


def test_model_quality_fine_omits_out_flag(tmp_path, script_file, monkeypatch, capsys):
    argv_out = tmp_path / "argv.json"
    monkeypatch.setenv("STUB_MODE", "ok")
    monkeypatch.setenv("STUB_ARGV_OUT", str(argv_out))
    out = tmp_path / "part.stl"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--quality", "fine",
                        "--solidcraft", str(STUB), "--no-save-design", "--json"])
    assert code == 0
    argv = json.loads(argv_out.read_text(encoding="utf-8"))
    assert "--out" not in argv


def test_model_saves_editable_design(tmp_path, script_file, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    out = tmp_path / "part.stl"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--solidcraft", str(STUB), "--json"])
    assert code == 0
    gate = _last_json(capsys)
    assert (tmp_path / "part.sc").is_file()
    assert gate["data"]["design"] == str(tmp_path / "part.sc")


def test_model_applies_transform_after_build(tmp_path, script_file, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    out = tmp_path / "big.stl"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--scale", "2", "--center",
                        "--solidcraft", str(STUB), "--no-save-design", "--json"])
    assert code == 0
    back = trimesh.load(str(out), force="mesh")
    assert isinstance(back, trimesh.Trimesh)
    assert list(back.extents) == pytest.approx([20, 20, 20], abs=1e-3)


# ---------------------------------------------------------------------------
# STEP
# ---------------------------------------------------------------------------

def test_model_step_skips_mesh_check(tmp_path, script_file, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    out = tmp_path / "part.step"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--solidcraft", str(STUB),
                        "--no-save-design", "--json"])
    assert code == 0
    gate = _last_json(capsys)
    assert gate["status"] == "PASS"
    assert gate["data"]["inspection"] is None
    assert any("B-rep" in note for note in gate["data"]["notes"])
    assert out.is_file()


# ---------------------------------------------------------------------------
# failures
# ---------------------------------------------------------------------------

def test_model_reports_solidcraft_failure(tmp_path, script_file, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "fail")
    out = tmp_path / "part.stl"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--solidcraft", str(STUB),
                        "--no-save-design", "--json"])
    assert code == 1
    gate = _last_json(capsys)
    assert gate["status"] == "FAIL"
    assert "stub exploded" in gate["reason"]
    assert not out.exists()


def test_model_treats_silent_run_as_failure(tmp_path, script_file, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "silent")
    out = tmp_path / "part.stl"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--solidcraft", str(STUB),
                        "--no-save-design", "--json"])
    assert code == 1
    assert "wrote no output" in _last_json(capsys)["reason"]


def test_model_without_solidcraft_returns_unverified(tmp_path, script_file,
                                                     monkeypatch, capsys):
    monkeypatch.setattr(sc, "probe", lambda explicit=None: {
        "installed": False, "path": None, "version": None, "source": None,
        "message": sc.MISSING_MESSAGE, "tried": [],
    })
    out = tmp_path / "part.stl"
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(out), "--json"])
    assert code == 2
    gate = _last_json(capsys)
    assert gate["status"] == "UNVERIFIED"
    assert gate["reason"] == sc.MISSING_MESSAGE
    assert not out.exists()


def test_model_rejects_format_solidcraft_cannot_export(tmp_path, script_file,
                                                       monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    code = fabric.main(["--action", "model", "--script", str(script_file),
                        "--output", str(tmp_path / "part.glb"),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 2
    assert "cannot export" in _last_json(capsys)["reason"]


def test_model_needs_a_script(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUB_MODE", "ok")
    code = fabric.main(["--action", "model", "--output", str(tmp_path / "p.stl"),
                        "--solidcraft", str(STUB), "--json"])
    assert code == 2
    assert "needs --script" in _last_json(capsys)["reason"]


# ---------------------------------------------------------------------------
# probe action through the CLI
# ---------------------------------------------------------------------------

def test_probe_action_exit_zero(monkeypatch, capsys):
    monkeypatch.setattr(sc, "probe", lambda explicit=None: {
        "installed": True, "path": str(STUB),
        "version": "solidcraft-cli 9.9.9-stub", "source": "explicit",
        "message": "SolidCraft CLI ready", "tried": [],
    })
    assert fabric.main(["--action", "probe", "--json"]) == 0


def test_probe_action_exit_two_when_missing(monkeypatch, capsys):
    monkeypatch.setattr(sc, "probe", lambda explicit=None: {
        "installed": False, "path": None, "version": None, "source": None,
        "message": sc.MISSING_MESSAGE, "tried": [],
    })
    assert fabric.main(["--action", "probe", "--json"]) == 2
    assert _last_json(capsys)["reason"] == sc.MISSING_MESSAGE
