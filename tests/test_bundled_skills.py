"""The bundled Blender half: thirty skills, verbatim, correctly attributed.

From 1.1.0 the plugin ships the Blender skill family beside the CAD skill. These
tests keep the claims in the README honest: the skills are there, their
frontmatter still names them, every one of them is bound to a Blender MCP tool
set, the relative links between them resolve inside the bundle, and the files
match the hashes recorded in ``skills/vendored.json``.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = PLUGIN_ROOT / "skills"
INSTALL = PLUGIN_ROOT / "install.py"

# Production family (11), HUD and animation QA (2), reference reconstruction
# pipeline (17) — the complete set published by cc-blender-skill.
BLENDER_SKILLS = [
    "text-to-blender",
    "blender-animation",
    "blender-cameras",
    "blender-export",
    "blender-lighting",
    "blender-materials",
    "blender-modeling",
    "blender-pro-workflow",
    "blender-rendering",
    "blender-skill-harmonizer",
    "blender-uv-texturing",
    "orbital-hud-motion",
    "animation-quality-gate",
    "atlas-uv-fitting",
    "closed-surface-uv-coverage",
    "contour-to-mesh",
    "fit-repair-optimizer",
    "landmark-fit-repair",
    "mascot-logo-reconstruction",
    "multiview-constraint-solver",
    "multiview-fit-loop",
    "orthographic-registration",
    "quality-refinement-autoloop",
    "reference-analysis-validator",
    "reference-look-calibration",
    "reference-to-3d",
    "source-part-segmentation",
    "texture-driven-mesh-fitting",
    "texture-state-animation",
    "wireframe-to-3d",
]


def frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path} has no frontmatter"
    block = text.split("---", 2)[1]
    return dict(
        line.split(":", 1) for line in block.strip().splitlines() if ":" in line
    )


def test_all_thirty_skills_are_present():
    missing = [s for s in BLENDER_SKILLS if not (SKILLS / s / "SKILL.md").is_file()]
    assert not missing, missing


def test_every_skill_frontmatter_names_its_directory():
    for name in ["3d-fabric", *BLENDER_SKILLS]:
        meta = frontmatter(SKILLS / name / "SKILL.md")
        assert meta["name"].strip() == name, (name, meta.get("name"))


def test_blender_skills_are_bound_to_a_blender_mcp():
    """The premise of the bundle: the pipeline skills declare Blender MCP tools.

    ``multiview-constraint-solver`` and ``source-part-segmentation`` are the two
    exceptions upstream: one reasons about reference views and emits constraints
    before anything is built, the other plans how a reference is split into
    parts. Neither needs a Blender tool.
    """
    mcp_free = {"multiview-constraint-solver", "source-part-segmentation"}
    for name in BLENDER_SKILLS:
        meta = frontmatter(SKILLS / name / "SKILL.md")
        tools = meta.get("allowed-tools", "")
        if name in mcp_free:
            assert "mcp__blender" not in tools, name
            continue
        assert "mcp__blender__" in tools or "mcp__blender_official__" in tools, name


def test_relative_links_between_skills_resolve_inside_the_bundle():
    pattern = re.compile(r"\(\.\./([A-Za-z0-9_.-]+)/")
    broken = []
    for name in BLENDER_SKILLS:
        for path in (SKILLS / name).rglob("*.md"):
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                if not (SKILLS / target).is_dir():
                    broken.append(f"{path.relative_to(SKILLS)} -> ../{target}/")
    assert not broken, broken


def test_vendored_manifest_matches_the_files():
    manifest = json.loads((SKILLS / "vendored.json").read_text(encoding="utf-8"))
    assert manifest["license"] == "MIT"
    assert "RobLe3" in manifest["copyright"]
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["commit"]), "record the upstream commit"
    assert sorted(manifest["skills"]) == sorted(BLENDER_SKILLS)

    files = manifest["files"]
    assert len(files) >= 125
    for relative, expected in files.items():
        actual = hashlib.sha256((SKILLS / relative).read_bytes()).hexdigest()
        assert actual == expected, f"{relative} changed; update skills/vendored.json"


def test_licence_text_travels_with_the_skills():
    text = (PLUGIN_ROOT / "licenses" / "cc-blender-skill-LICENSE.txt").read_text(
        encoding="utf-8"
    )
    assert "MIT License" in text
    assert "Copyright (c) 2026 RobLe3" in text


def test_the_cad_skill_routes_to_the_blender_half():
    text = (SKILLS / "3d-fabric" / "SKILL.md").read_text(encoding="utf-8")
    assert "text-to-blender" in text
    assert "mcp__blender__" in text


def test_plain_install_carries_the_licence_text(tmp_path):
    target = tmp_path / "skills" / "3d-fabric"
    proc = subprocess.run(
        [sys.executable, str(INSTALL), "--skill-dir", str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(PLUGIN_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    copied = target / "licenses" / "cc-blender-skill-LICENSE.txt"
    assert copied.is_file()
    assert "RobLe3" in copied.read_text(encoding="utf-8")
