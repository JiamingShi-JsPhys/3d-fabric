# Install commands

Every per-host command, the `install.py` flags and the optional capabilities. Methods 1 and 3 are short enough to stay in the README: [3d-fabric](../README.md) · [简体中文](INSTALL_COMMANDS_zh.md)

---

## Prerequisite: SolidCraft

3d-fabric ships no solid kernel; it drives a SolidCraft installation you already have. SolidCraft is open source and free (MIT / Apache-2.0 dual licence) and has to be installed separately:

| Platform | Download |
| --- | --- |
| Windows | [solidcraft-windows-x64.msi](https://github.com/tangency-labs/solidcraft/releases/latest/download/solidcraft-windows-x64.msi) |
| macOS | [solidcraft-macos-universal.dmg](https://github.com/tangency-labs/solidcraft/releases/latest/download/solidcraft-macos-universal.dmg) (Apple silicon and Intel) |
| Linux | [solidcraft-linux-x86_64.AppImage](https://github.com/tangency-labs/solidcraft/releases/latest/download/solidcraft-linux-x86_64.AppImage), or `sudo snap install solidcraft` |

- Everything else — ARM64 and 32-bit builds, portable zip, `.deb`, `.rpm`, Flatpak — is on the [downloads page](https://solidcraft.io/download).
- The Windows downloads are not code-signed yet, so SmartScreen stops you once: **More info → Run anyway**.
- The browser build at <https://solidcraft.io> needs no install, but it exposes no `solidcraft-cli`, so **this plugin cannot use it**.

Confirm the CLI is reachable:

```bash
solidcraft-cli --version
```

A version line such as `solidcraft-cli 0.30.1` — the one this plugin is verified against — means you are done; a newer release works too. Silence means it is not on `PATH` (older Windows installers do not add it); tell the plugin where it is, either way:

```bash
python run.py --action probe --solidcraft "C:/Program Files/SolidCraft/solidcraft-cli.exe"
```

```bash
set SOLIDCRAFT_CLI=C:\Program Files\SolidCraft\solidcraft-cli.exe
```

On macOS and Linux use `export` instead of `set`. `SOLIDCRAFT_HOME` pointing at the install folder works too.

> **Only four actions need SolidCraft**: `model`, `script`, `measure`, `snapshot`. `inspect` and `repair` do not — a mesh from a scanner, a download or another CAD package stays checkable and repairable on a machine that has never installed SolidCraft.

---

### Prerequisite: Blender (only if you want that half)

The thirty Blender skills need two things, both from the Blender ecosystem and neither bundled here:

1. **A local Blender** — <https://www.blender.org/download/> (4.x is fine)
2. **A Blender MCP server**, exposing Blender as the `mcp__blender__*` or `mcp__blender_official__*` tool set

With either missing, the Blender skills say what is missing rather than describing a render they did not make. The CAD half is unaffected — `run.py` never touches Blender.

---

## Method 2: install with commands

**Claude Code** — from your shell, marketplace and install in one step:

```bash
claude plugin install 3d-fabric --marketplace https://github.com/JiamingShi-JsPhys/3d-fabric.git
```

**Claude Code** — from inside a session, add the marketplace pinned to the release tag:

```text
/plugin marketplace add https://github.com/JiamingShi-JsPhys/3d-fabric.git#v1.1.1
```

Then install the entry it lists:

```text
/plugin install 3d-fabric@3d-fabric-marketplace
```

**Codex** — register the URL as a Git marketplace; `--ref` pins the release tag, and an SSH URL or a local path works in place of the HTTPS one:

```bash
codex plugin marketplace add https://github.com/JiamingShi-JsPhys/3d-fabric.git --ref v1.1.1
```

```bash
codex plugin add 3d-fabric@3d-fabric-marketplace
```

**dsh (DeepSeek Harness)** — dsh installs plugins as npm packages, so the repository carries a `package.json` and a `cordis.patch.yml` beside the Claude Code manifests, and `index.js` registers the skill with dsh's skill registry:

```bash
dsh plugin --profile desktop add github:JiamingShi-JsPhys/3d-fabric#v1.1.1
```

dsh refuses any package whose `package.json` lacks `dsh.bundle.patch` — that is the *"这个包没有声明组合包"* refusal (`reasonNotBundle`). Upgrading means uninstalling first; dsh does not replace an installed version in place.

**CodeBuddy** — the same shape as Claude Code:

```text
/plugin marketplace add https://github.com/JiamingShi-JsPhys/3d-fabric.git#v1.1.1
```

```text
/plugin install 3d-fabric@3d-fabric-marketplace
```

**Cursor, Windsurf, Cline, Continue, Roo Code, GitHub Copilot, opencode** — each reads a rule file from its own location, and none of them accepts this repository as a plugin: Cline's plugins are JS/TS packages, Cursor packs plugins its own way, and `opencode plugin <module>` installs npm modules. **No vendor ships an installer that understands another vendor's rule file**, so this repository ships one:

```bash
git clone https://github.com/JiamingShi-JsPhys/3d-fabric.git && python 3d-fabric/install.py --project <your-project>
```

That one command writes every project-scoped rule file at once:

- `.cursor/rules/3d-fabric.mdc` (`alwaysApply`)
- `.windsurf/rules/3d-fabric.md` (`trigger: always_on`)
- `.clinerules/3d-fabric.md`
- `.continue/rules/3d-fabric.md` (`alwaysApply`)
- `.roo/rules/3d-fabric.md`
- `.github/copilot-instructions.md`
- `AGENTS.md` — the generic contract Codex, opencode and Copilot agents also read

`--global` adds the two user-scoped files: `~/.config/opencode/AGENTS.md` and `$CODEX_HOME/AGENTS.md` (default `~/.codex/`), skipping any host this machine does not have. Claude Code is deliberately excluded there — it has a plugin channel, and `~/.claude/CLAUDE.md` belongs to the user.

Keep the cloned repository where the agent can reach it: every rule file names `run.py` and `scripts/`, so the host drives the same engine a plugin host would. A rule file describes *how to call*, and carries no code.

Re-running is safe: an identical file reports `unchanged`, and a rule file that has drifted is left alone unless you pass `--force`. Every rule file is `AGENTS.md` verbatim behind that host's header, so one edit to the contract reaches all six — and `tests/test_plugin_manifests.py` fails if they drift apart.

**opencode can skip the copy entirely** — point `opencode.json`'s `instructions` array at the rule file in place:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["../3d-fabric/AGENTS.md"]
}
```

---

## Every `install.py` flag

```text
python install.py                      # same as --check
python install.py --check              # report python / geometry stack / SolidCraft / examples
python install.py --deps               # pip install -r requirements.txt
python install.py --skill-dir [PATH]   # copy the skill into a host skill dir (default ~/.claude/skills/3d-fabric)
python install.py --project <dir>      # write every project-scoped rule file
python install.py --global             # write user-scoped rules, skipping absent hosts
python install.py --only cursor,codex  # narrow to a subset
python install.py --list               # list destinations, write nothing
python install.py --dry-run            # preview
python install.py --force              # overwrite an existing target
```

`--check` reports its four checks one by one; any failure says what is missing and how to add it.

---

## Manual: no plugin system at all

Clone and run it in place:

```bash
python -m pip install -r requirements.txt
python run.py --action probe
```

Or copy the skill together with what it imports into a skill directory:

```bash
python install.py --skill-dir ~/.claude/skills/3d-fabric
```

`--skill-dir` copies `run.py`, `scripts/` and `references/` along with the skill, but it installs the CAD skill only; the thirty Blender skills travel through the plugin channel, where their per-skill `allowed-tools` are honoured. Commands inside it are written as `python "${CLAUDE_PLUGIN_ROOT:-.}/run.py"`, which falls back to the skill directory when the plugin variable is absent.

---

## Optional capabilities and dependencies

```bash
pip install -r requirements.txt    # core: trimesh, numpy, scipy
pip install numpy-stl              # tests only: an independent STL reader
```

The full capability/dependency/missing-behaviour matrix is in [DEPENDENCIES.md](DEPENDENCIES.md). `inspect` and `repair` need only trimesh; `model`, `script`, `measure` and `snapshot` additionally need a local SolidCraft.
