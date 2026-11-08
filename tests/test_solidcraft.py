"""Bridge tests — probe, script execution and output verification.

The CLI itself is replaced by ``tests/stub_solidcraft.py`` so the suite passes
with or without SolidCraft installed. When the real CLI *is* present, one
integration test runs against it and is skipped otherwise.
"""

from __future__ import annotations

import json
import pathlib
import shutil

import pytest

from scripts import solidcraft as sc  # pyright: ignore[reportAttributeAccessIssue]

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
STUB = pathlib.Path(__file__).resolve().parent / "stub_solidcraft.py"

SCRIPT = {
    "commands": [
        {"command": "solid.box", "params": {"length": 10, "width": 10, "height": 10}}
    ]
}


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def test_probe_finds_explicit_stub():
    info = sc.probe(str(STUB))
    assert info["installed"] is True
    assert info["path"] == str(STUB)
    assert info["version"] == "solidcraft-cli 9.9.9-stub"
    assert info["source"] == "explicit"


def test_probe_reports_missing_without_touching_the_disk(monkeypatch):
    monkeypatch.setattr(sc.shutil, "which", lambda name: None)
    monkeypatch.setattr(sc, "_known_paths", lambda: [])
    monkeypatch.delenv("SOLIDCRAFT_CLI", raising=False)
    monkeypatch.delenv("SOLIDCRAFT_HOME", raising=False)

    info = sc.probe(str(PLUGIN_ROOT / "no-such-cli.exe"))
    assert info["installed"] is False
    assert info["path"] is None
    assert info["message"] == sc.MISSING_MESSAGE


def test_probe_reads_env_var(monkeypatch):
    monkeypatch.setattr(sc.shutil, "which", lambda name: None)
    monkeypatch.setattr(sc, "_known_paths", lambda: [])
    monkeypatch.setenv("SOLIDCRAFT_CLI", str(STUB))
    info = sc.probe()
    assert info["installed"] is True
    assert info["source"] == "SOLIDCRAFT_CLI"


def test_probe_rejects_a_file_that_is_not_a_cli(tmp_path):
    fake = tmp_path / "fake-cli.exe"
    fake.write_text("not a program", encoding="utf-8")
    info = sc.probe(str(fake))
    # a file that cannot answer --version is never accepted as the CLI
    assert info["path"] != str(fake)


# ---------------------------------------------------------------------------
# script helpers
# ---------------------------------------------------------------------------

def test_materialize_script_roundtrip(tmp_path):
    path = sc.materialize_script(SCRIPT["commands"], tmp_path / "build.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["commands"][0]["command"] == "solid.box"


def test_materialize_rejects_empty_commands(tmp_path):
    with pytest.raises(sc.SolidCraftError, match="no commands"):
        sc.materialize_script([], tmp_path / "x.json")


def test_with_export_adds_quality(tmp_path):
    out = tmp_path / "part.stl"
    commands = sc.with_export(SCRIPT["commands"], out, "stl", "fine")
    export = commands[-1]
    assert export["command"] == "file.export_stl"
    assert export["params"]["path"] == str(out)
    assert export["params"]["quality"] == "fine"
    # the original list is not mutated
    assert len(SCRIPT["commands"]) == 1


def test_with_export_step_has_no_quality(tmp_path):
    commands = sc.with_export(SCRIPT["commands"], tmp_path / "p.step", "step", "fine")
    assert commands[-1]["command"] == "file.export_step"
    assert "quality" not in commands[-1]["params"]


def test_with_export_rejects_unknown_format(tmp_path):
    with pytest.raises(sc.SolidCraftError, match="no export command"):
        sc.with_export(SCRIPT["commands"], tmp_path / "p.glb", "glb", "fine")


def test_read_commands(tmp_path):
    path = sc.materialize_script(SCRIPT["commands"], tmp_path / "s.json")
    assert sc.read_commands(path) == SCRIPT["commands"]
    assert sc.read_commands(tmp_path / "missing.json") is None


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def test_run_writes_outputs(tmp_path):
    script = sc.materialize_script(SCRIPT["commands"], tmp_path / "s.json")
    out = tmp_path / "out.stl"
    result = sc.run(STUB, script, [out], timeout=60)
    assert result["ok"] is True
    assert out.is_file() and out.stat().st_size > 0
    assert isinstance(result["results"], list)
    # the results sidecar is cleaned up unless asked for
    assert not (tmp_path / ".3d-fabric-results.json").exists()


def test_run_keeps_results_when_asked(tmp_path):
    script = sc.materialize_script(SCRIPT["commands"], tmp_path / "s.json")
    out = tmp_path / "out.stl"
    sc.run(STUB, script, [out], timeout=60, keep_results=True)
    assert (tmp_path / ".3d-fabric-results.json").is_file()


def test_run_reports_failure_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "fail")
    script = sc.materialize_script(SCRIPT["commands"], tmp_path / "s.json")
    out = tmp_path / "out.stl"
    result = sc.run(STUB, script, [out], timeout=60)
    assert result["ok"] is False
    assert result["returncode"] == 1
    assert "stub exploded" in result["error"]
    assert not out.exists()


def test_run_catches_silent_success(tmp_path, monkeypatch):
    """Exit 0 with no file must not be mistaken for success."""
    monkeypatch.setenv("STUB_MODE", "silent")
    script = sc.materialize_script(SCRIPT["commands"], tmp_path / "s.json")
    out = tmp_path / "out.stl"
    result = sc.run(STUB, script, [out], timeout=60)
    assert result["ok"] is False
    assert "wrote no output" in result["error"]


def test_run_checks_expected_even_without_out_flags(tmp_path):
    """Quality injection passes no --out; the script exports instead."""
    out = tmp_path / "out.stl"
    commands = sc.with_export(SCRIPT["commands"], out, "stl", "fine")
    script = sc.materialize_script(commands, tmp_path / "s.json")
    result = sc.run(STUB, script, [], expected=[out], timeout=60)
    assert result["ok"] is True
    assert out.is_file()


def test_run_timeout_is_reported(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise sc.subprocess.TimeoutExpired(cmd="stub", timeout=1)

    monkeypatch.setattr(sc.subprocess, "run", fake_run)
    script = sc.materialize_script(SCRIPT["commands"], tmp_path / "s.json")
    with pytest.raises(sc.SolidCraftError, match="did not finish"):
        sc.run(STUB, script, [tmp_path / "out.stl"], timeout=1)


def test_run_missing_cli_raises(tmp_path):
    with pytest.raises(sc.SolidCraftError, match="not found"):
        sc.run(tmp_path / "nope.exe", tmp_path / "s.json", [tmp_path / "o.stl"])


# ---------------------------------------------------------------------------
# integration (real SolidCraft, when installed)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("solidcraft-cli") is None
                    and not pathlib.Path("D:/Applications/SolidCraft/solidcraft-cli.exe").is_file(),
                    reason="SolidCraft is not installed on this machine")
def test_real_solidcraft_builds_a_box(tmp_path):
    info = sc.probe()
    assert info["installed"] is True
    script = sc.materialize_script(SCRIPT["commands"], tmp_path / "box.json")
    out = tmp_path / "box.stl"
    result = sc.run(info["path"], script, [out], timeout=180)
    assert result["ok"] is True, result["error"]
    assert out.stat().st_size > 84  # header + at least one triangle
