"""The platform half: one repository, every host that can load it.

Four hosts read a plugin manifest (Claude Code, CodeBuddy, Codex, dsh) and six
more read a plain rule file (Cursor, Windsurf, Cline, Continue, Roo Code,
GitHub Copilot). None of them validates another's format, and a manifest that
disagrees with its siblings is invisible until somebody installs from the host
it belongs to — so the shape is locked here.

The rule files are not independent documents: every one of them is `AGENTS.md`
with a host-specific frontmatter block in front. That is what makes one edit to
`AGENTS.md` reach six hosts, and what this file checks.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

PLUGIN_DIRS = {
    "claude": PLUGIN_ROOT / ".claude-plugin",
    "codebuddy": PLUGIN_ROOT / ".codebuddy-plugin",
    "codex": PLUGIN_ROOT / ".codex-plugin",
    "dsh": PLUGIN_ROOT / ".dsh-plugin",
}

# Hosts whose plugin.json follows the Claude Code contract.
CLAUDE_STYLE = ("claude", "codebuddy", "codex")

# Host -> rule file it reads, relative to a project root. `AGENTS.md` is the
# generic contract Codex, opencode and the Copilot agents fall back to.
RULE_FILES = {
    "cursor": ".cursor/rules/3d-fabric.mdc",
    "windsurf": ".windsurf/rules/3d-fabric.md",
    "cline": ".clinerules/3d-fabric.md",
    "continue": ".continue/rules/3d-fabric.md",
    "roo": ".roo/rules/3d-fabric.md",
    "copilot": ".github/copilot-instructions.md",
    "agents": "AGENTS.md",
}


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def version() -> str:
    """Single source of truth: manifest.json, which the runtime also reads."""
    return load(PLUGIN_ROOT / "manifest.json")["version"]


def body_of(path: pathlib.Path) -> str:
    """A rule file minus its optional frontmatter block."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            rest = text.index("\n", end + 1)
            if rest != -1:
                # rule files put one blank line between the header and the body
                return text[rest + 1 :].lstrip("\n")
    return text


def test_every_host_has_a_manifest_directory():
    for host, path in PLUGIN_DIRS.items():
        assert path.is_dir(), f"missing plugin directory for {host}: {path}"


def test_no_manifest_carries_the_fields_that_get_a_plugin_ignored():
    """`author` must be an object; `skills` and `icon` stay out.

    A bare-string author, an `icon` path, or a string `skills` field makes a
    host drop the plugin without an error message — the failure mode these
    hosts share and the only one worth locking down by shape.
    """
    for host in CLAUDE_STYLE:
        data = load(PLUGIN_DIRS[host] / "plugin.json")
        assert data["name"] == "3d-fabric", host
        author = data.get("author")
        assert isinstance(author, dict), f"{host}: author must be an object"
        assert isinstance(author.get("name"), str) and author["name"].strip(), host
        assert "skills" not in data, f"{host}: omit 'skills' so skills/ is auto-scanned"
        assert "icon" not in data, host


def test_every_manifest_agrees_on_the_version():
    seen = {"manifest.json": version()}
    for host, directory in PLUGIN_DIRS.items():
        seen[f"{host}/plugin.json"] = load(directory / "plugin.json")["version"]
    seen["package.json"] = load(PLUGIN_ROOT / "package.json")["version"]
    distinct = set(seen.values())
    assert len(distinct) == 1, seen
    assert distinct.pop() == version()


def test_the_codex_entry_carries_its_interface_block():
    data = load(PLUGIN_DIRS["codex"] / "plugin.json")
    interface = data.get("interface")
    assert isinstance(interface, dict), "codex reads displayName/category from interface"
    assert interface["displayName"] and interface["category"]


def test_every_marketplace_lists_the_plugin_at_the_current_version():
    for host in CLAUDE_STYLE:
        data = load(PLUGIN_DIRS[host] / "marketplace.json")
        entries = data.get("plugins")
        assert isinstance(entries, list) and entries, host
        entry = entries[0]
        assert entry["name"] == "3d-fabric", host
        assert entry["source"] == "./", host
        assert entry["version"] == version(), f"{host}: marketplace version drifted"
        owner = data.get("owner")
        if owner is not None:
            assert isinstance(owner.get("name"), str) and owner["name"], host


def test_the_dsh_manifest_points_at_a_real_entry():
    data = load(PLUGIN_DIRS["dsh"] / "plugin.json")
    assert data["name"] == "3d-fabric"
    main = data.get("main")
    assert main, "dsh plugin.json must declare main"
    assert (PLUGIN_DIRS["dsh"] / main).is_file(), f"missing {main}"


def test_both_dsh_entries_expose_name_and_apply():
    for path in (PLUGIN_DIRS["dsh"] / "index.js", PLUGIN_ROOT / "index.js"):
        assert path.is_file(), f"missing CJS entry: {path}"
        text = path.read_text(encoding="utf-8")
        assert "name" in text and "apply" in text, path


def test_the_directory_entry_delegates_to_the_package_entry():
    """Two entries, one implementation: the .dsh-plugin copy must not drift."""
    text = (PLUGIN_DIRS["dsh"] / "index.js").read_text(encoding="utf-8")
    assert "require('../index.js')" in text


def test_every_rule_file_is_agents_md_with_a_host_header():
    contract = (PLUGIN_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert contract.startswith("# 3d-fabric"), "AGENTS.md lost its title"
    for host, relative in RULE_FILES.items():
        path = PLUGIN_ROOT / relative
        assert path.is_file(), f"{host}: missing rule file {relative}"
        assert body_of(path) == contract, f"{host}: {relative} drifted from AGENTS.md"


def test_the_rule_headers_match_what_each_host_documents():
    frontmatter = {
        "cursor": ("alwaysApply: true", ".cursor/rules/3d-fabric.mdc"),
        "continue": ("alwaysApply: true", ".continue/rules/3d-fabric.md"),
        "windsurf": ("trigger: always_on", ".windsurf/rules/3d-fabric.md"),
    }
    for host, (marker, relative) in frontmatter.items():
        text = (PLUGIN_ROOT / relative).read_text(encoding="utf-8")
        assert text.startswith("---"), host
        header = text.split("---", 2)[1]
        assert marker in header, f"{host}: expected {marker!r} in the header"
        assert f"v{version()}" in header, f"{host}: header carries a stale version"
    for host in ("roo", "cline", "copilot"):
        text = (PLUGIN_ROOT / RULE_FILES[host]).read_text(encoding="utf-8")
        assert not text.startswith("---"), f"{host}: this host reads no frontmatter"


def test_the_installer_lists_every_host():
    proc = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "install.py"), "--list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PLUGIN_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    for host in RULE_FILES:
        assert host in proc.stdout, f"install.py --list does not mention {host}"
    assert "opencode" in proc.stdout and "codex" in proc.stdout
