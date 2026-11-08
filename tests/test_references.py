"""The bundled SolidCraft references: present, unmodified, correctly attributed.

`references/solidcraft/` holds SolidCraft's own agent documents verbatim under
the MIT option of its dual licence. These tests keep the promise the README
makes: the files are there, the hashes match the provenance table, the licence
travels with them, and an install carries the folder along.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import shutil
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
REFS = PLUGIN_ROOT / "references" / "solidcraft"
INSTALL = PLUGIN_ROOT / "install.py"

REQUIRED = [
    "solidcraft-modeling/SKILL.md",
    "solidcraft-modeling/reference.md",
    "solidcraft-editing/SKILL.md",
    "solidcraft-mechanisms/SKILL.md",
    "solidcraft-mechanisms/reference.md",
    "solidcraft-checking/SKILL.md",
    "solidcraft-checking/reference/porting.md",
    "solidcraft-checking/scripts/run.py",
    "solidcraft-checking/scripts/scb.py",
    "solidcraft-checking/scripts/compare_step.py",
    "solidcraft-checking/templates/test_design.py",
    "LICENSE-MIT",
    "NOTICE",
]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_every_reference_file_is_present():
    missing = [rel for rel in REQUIRED if not (REFS / rel).is_file()]
    assert not missing, missing


def test_licence_and_notice_carry_the_upstream_copyright():
    lic = (REFS / "LICENSE-MIT").read_text(encoding="utf-8")
    assert "MIT License" in lic
    assert "Copyright (c) 2026 SolidCraft contributors" in lic
    assert "The above copyright notice and this permission notice" in lic

    notice = (REFS / "NOTICE").read_text(encoding="utf-8")
    assert notice.startswith("SolidCraft")
    assert "MIT License or the Apache License" in notice


def test_provenance_table_matches_the_files():
    """Every hash in references/solidcraft/README.md must match its file."""
    readme = (REFS / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", readme, re.MULTILINE)
    assert len(rows) >= len(REQUIRED), "provenance table lost rows"

    for upstream_path, expected in rows:
        # `skills/solidcraft-x/...` is stored as `solidcraft-x/...`;
        # everything else (LICENSE-MIT, NOTICE) sits at the root.
        relative = upstream_path.removeprefix("skills/")
        actual = sha256(REFS / relative)
        assert actual == expected, f"{upstream_path} changed; update the README table"


def test_plugin_skill_points_at_a_real_reference():
    skill = (PLUGIN_ROOT / "skills" / "3d-fabric" / "SKILL.md").read_text(encoding="utf-8")
    assert "references/solidcraft/solidcraft-modeling/reference.md" in skill
    assert (PLUGIN_ROOT / "references" / "solidcraft"
            / "solidcraft-modeling" / "reference.md").is_file()


def test_skill_dir_install_copies_the_references(tmp_path):
    target = tmp_path / "skills" / "3d-fabric"
    proc = subprocess.run(
        [sys.executable, str(INSTALL), "--skill-dir", str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(PLUGIN_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    copied = target / "references" / "solidcraft" / "solidcraft-modeling" / "reference.md"
    assert copied.is_file()
    assert sha256(copied) == sha256(REFS / "solidcraft-modeling" / "reference.md")
    assert (target / "references" / "solidcraft" / "LICENSE-MIT").is_file()

    shutil.rmtree(tmp_path, ignore_errors=True)
