"""The dsh half: the package manifest a DeepSeek Harness install reads.

dsh installs a plugin as an npm package and then mounts it as a cordis plugin.
It refuses any package whose ``package.json`` does not declare
``dsh.bundle.patch`` (``reasonNotBundle`` — "这个包没有声明组合包"), which is
what 1.0.0 hit: the repository had no ``package.json``, pnpm wrote a
placeholder, and dsh found nothing to mount. These tests keep that from
happening again without anybody noticing.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = PLUGIN_ROOT / "package.json"
PATCH = PLUGIN_ROOT / "cordis.patch.yml"
ENTRY = PLUGIN_ROOT / "index.js"


def read_package() -> dict:
    return json.loads(PACKAGE.read_text(encoding="utf-8"))


def test_the_package_declares_a_dsh_bundle():
    package = read_package()
    assert package["name"] == "3d-fabric"
    bundle = package["dsh"]["bundle"]
    patch = bundle["patch"]
    assert isinstance(patch, str) and patch.strip() != "", "name the patch file"
    resolved = (PLUGIN_ROOT / patch).resolve()
    assert resolved.is_file(), f"{patch} does not exist"
    assert resolved == PATCH.resolve()


def test_the_entry_point_is_the_one_dsh_will_load():
    package = read_package()
    assert package["main"] == "index.js"
    assert ENTRY.is_file()


def test_the_patch_inserts_this_package():
    text = PATCH.read_text(encoding="utf-8")
    assert text.lstrip().startswith("- insert:"), text
    assert re.search(r"^\s*-?\s*id:\s*3d-fabric\s*$", text, re.MULTILINE), text
    assert re.search(r"^\s*name:\s*3d-fabric\s*$", text, re.MULTILINE), text


def test_both_manifests_agree_on_the_version():
    """A dsh install and a Claude Code install must not drift apart."""
    package = read_package()
    plugin = json.loads(
        (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    marketplace = json.loads(
        (PLUGIN_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((PLUGIN_ROOT / "manifest.json").read_text(encoding="utf-8"))
    listed = [entry["version"] for entry in marketplace["plugins"]]
    assert package["version"] == plugin["version"] == manifest["version"]
    assert package["version"] in listed


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_entry_point_lists_the_bundled_skills():
    script = """
const m = require('./index.js');
const skills = m.collectSkills();
const out = { name: m.name, inject: m.inject, skills: skills.map((s) => s.name) };
let provider = null;
m.apply({ skills: { registerProvider: (factory) => { provider = factory(); } } });
if (provider === null) { console.error('provider was not registered'); process.exit(1); }
provider.list().then(async (candidates) => {
  const definition = await provider.get(candidates[0]);
  out.candidates = candidates.length;
  out.content = definition.content.length;
  out.base = definition.resourceBase.path;
  console.log(JSON.stringify(out));
});
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PLUGIN_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result["name"] == "3d-fabric"
    assert result["inject"] == ["skills"]
    expected = sorted(
        path.parent.name for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")
    )
    assert result["skills"] == expected
    assert result["candidates"] == len(expected)
    assert result["content"] > 0
    assert pathlib.Path(result["base"]) == (PLUGIN_ROOT / "skills").resolve()
