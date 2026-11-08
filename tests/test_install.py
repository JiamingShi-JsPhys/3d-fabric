"""Installer tests — the environment check and the skill-directory copy.

Both run as subprocesses, the way the README tells a user to run them.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL = PLUGIN_ROOT / "install.py"


def run_install(*args):
    return subprocess.run(
        [sys.executable, str(INSTALL), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(PLUGIN_ROOT),
    )


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------

def test_check_reports_every_prerequisite():
    proc = run_install("--check")
    assert proc.returncode in (0, 2), proc.stderr
    for label in ("python", "geometry stack", "solidcraft", "examples"):
        assert label in proc.stdout
    assert "OK" in proc.stdout


def test_check_default_action():
    proc = run_install()
    assert proc.returncode in (0, 2)
    assert "3d-fabric · check" in proc.stdout


# ---------------------------------------------------------------------------
# --skill-dir
# ---------------------------------------------------------------------------

def test_skill_dir_dry_run_writes_nothing(tmp_path):
    target = tmp_path / "skills" / "3d-fabric"
    proc = run_install("--skill-dir", target, "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert "would copy" in proc.stdout
    assert not target.exists()


def test_skill_dir_copies_a_runnable_skill(tmp_path):
    target = tmp_path / "skills" / "3d-fabric"
    proc = run_install("--skill-dir", target)
    assert proc.returncode == 0, proc.stderr

    for relative in ("run.py", "scripts/engine.py", "scripts/solidcraft.py",
                     "SKILL.md", "requirements.txt", "LICENSE"):
        assert (target / relative).is_file(), f"missing {relative}"

    # the copied run.py must actually work from its new home
    probe = subprocess.run(
        [sys.executable, str(target / "run.py"), "--action", "probe", "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(target),
    )
    assert probe.returncode in (0, 2), probe.stderr
    assert "3d-fabric" in probe.stdout


def test_skill_dir_refuses_to_overwrite_without_force(tmp_path):
    target = tmp_path / "skills" / "3d-fabric"
    assert run_install("--skill-dir", target).returncode == 0
    second = run_install("--skill-dir", target)
    assert second.returncode == 1
    assert "already exists" in second.stderr

    forced = run_install("--skill-dir", target, "--force")
    assert forced.returncode == 0, forced.stderr


def test_skill_dir_missing_source_is_reported(tmp_path):
    # install.py resolves sources from its own location; run it from a bare
    # copy with no peers and it must fail loudly instead of half-copying
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    shutil.copy2(INSTALL, lonely / "install.py")
    proc = subprocess.run(
        [sys.executable, str(lonely / "install.py"),
         "--skill-dir", str(tmp_path / "out")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(lonely),
    )
    assert proc.returncode == 1
    assert "absent" in proc.stderr


# ---------------------------------------------------------------------------
# argument handling
# ---------------------------------------------------------------------------

def test_actions_are_mutually_exclusive():
    proc = run_install("--check", "--deps")
    assert proc.returncode != 0
    assert "not allowed" in proc.stderr
