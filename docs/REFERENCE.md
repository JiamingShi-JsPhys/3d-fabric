# 3d-fabric reference

Everything that does not belong in a quick start: the seven actions and their flags, the gate record, the exit codes, the dependency map, the repository layout and the test suite.

**English** · [简体中文](REFERENCE_zh.md)

## The seven actions

| Action | Does | Needs SolidCraft |
| --- | --- | --- |
| `probe` | Locate and verify the CLI | — (looks for it) |
| `model` | Run a script, export, auto-inspect; `--in` edits an existing design | **yes** |
| `script` | Turn a `.sc` / `.step` back into a `{"commands": [...]}` script | **yes** |
| `measure` | Volume, mass, area, bounds, face types and parameters from the B-rep | **yes** |
| `snapshot` | Render a PNG preview (views, sections, per-body styling) | **yes** |
| `inspect` | Print-quality report on any mesh | no |
| `repair` | Weld, fill holes, fix normals | no |

Every action accepts the same global flags:

| Flag | Meaning |
| --- | --- |
| `--action` | one of the seven above (required) |
| `--input` | the request `.json`, the `.sc` / `.step` design, or the mesh file |
| `--output` | where the result is written (repeats for `model`: one per `--format`) |
| `--solidcraft` | explicit path to `solidcraft-cli` |
| `--root` | workspace root; the gate lands under `<root>/process/gates/` |
| `--report` | write the gate JSON to this exact path |
| `--json` | print the gate as one JSON line on stdout |
| `--timeout` | seconds before the CLI call is abandoned (default 300) |

Per-action flags:

| Flag | Action | Meaning |
| --- | --- | --- |
| `--in`, `--design` | `model` | apply the script on top of an existing design, leaving it untouched |
| `--script` | `model` | the `{"commands": [...]}` file to apply with `--in` |
| `--format` | `model` | `stl` (default), `step`, `3mf`, `obj`; repeats |
| `--quality` | `model` | `standard`, `fine`, `finest` — injected into the script as a per-command export setting |
| `--prompt` | `model` | the natural-language request, recorded in the report |
| `--script-out` | `model` | where to write the materialised script |
| `--save-design` / `--no-save-design` | `model` | keep or skip the editable `.sc` beside the export |
| `--keep-results` | `model` | keep the per-step results sidecar; the path is in `data.results_path` |
| `--scale`, `--scale-xyz`, `--translate`, `--rotate`, `--center` | any | applied to the mesh after the build or before the report |
| `--no-fill-holes`, `--max-hole-loop`, `--planarity-tol`, `--ascii` | `repair` | skip filling, size limit for a fan-fill, planarity guard, ASCII STL |
| `--view`, `--width`, `--height`, `--section`, `--body` | `snapshot` | view name, image size, section cut, per-body styling (`NAME:opacity=0.3,color=#rrggbb`, repeats) |

## Gate records

Every action ends in one record, printed by `--json` and written to `--report` or, with `--root`, to
`<root>/process/gates/3d-fabric_<UTC stamp>.json`:

```json
{
  "skill": "3d-fabric",
  "status": "PASS",
  "evidence_level": "EMPIRICAL",
  "reason": "watertight, winding consistent, manifold",
  "artifacts": ["bracket.stl", "bracket.sc", "bracket.solidcraft.json"],
  "timestamp": "2026-11-12T10:21:33.412Z",
  "data": {
    "action": "inspect",
    "verdict": "ready_to_print",
    "printability": {
      "verdict": "ready_to_print",
      "repairable": true,
      "issues": []
    }
  }
}
```

`status` is `PASS`, `FAIL` or `UNVERIFIED`. `data` carries the per-action payload: the analysis for
`inspect`, the before/after topology for `repair`, the totals and per-body readings for `measure`, the
image path and size for `snapshot`, the recovered command list for `script`, and the step list, exit
code and stderr for anything that ran `solidcraft-cli`.

Gate filenames carry milliseconds, so two runs finishing in the same second write two files.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | `PASS` — the action succeeded and the gate passed |
| 1 | `FAIL` — the action could not complete, or the mesh is `blocked` |
| 2 | `UNVERIFIED` — the action ran but could not assert a verdict (`needs_repair`, SolidCraft missing, unreadable input) |

A usage error (unknown action, missing `--input`) also exits 2, because that is what argparse does;
the message on stderr distinguishes it from a gate verdict.

## Dependencies

`docs/DEPENDENCIES.md` is the capability × package × licence × required-or-optional matrix, including
what each action reports when a package is missing. In short: `trimesh`, `numpy` and `scipy` are
required; `numpy-stl` is test-only; SolidCraft is required by `model`, `script`, `measure` and
`snapshot`; Blender plus a Blender MCP server are required by the thirty bundled skills and by nothing
in `run.py`.

## Repository layout

```text
3d-fabric/
├── .claude-plugin/                   # Claude Code plugin manifest + marketplace
├── .clinerules/                      # Cline rule file
├── .codebuddy-plugin/                # CodeBuddy plugin manifest + marketplace
├── .codex-plugin/                    # Codex plugin manifest + marketplace (+ interface)
├── .continue/rules/                  # Continue rule file
├── .cursor/rules/                    # Cursor rule file (.mdc)
├── .dsh-plugin/                      # dsh directory entry (delegates to index.js)
├── .github/
│   ├── copilot-instructions.md       # GitHub Copilot rule file
│   └── workflows/ci.yml              # pytest on Linux and Windows, plus a CLI smoke test
├── .gitattributes                    # LF normalisation; binary meshes marked
├── .gitignore
├── .roo/rules/                       # Roo Code rule file
├── .windsurf/rules/                  # Windsurf rule file
├── AGENTS.md                         # agent operating rules — the body of all six rule files
├── CHANGELOG.md                      # release notes
├── LICENSE                           # MIT
├── README.md                         # quick start
├── README_zh.md                      # 简体中文
├── THIRD_PARTY_LICENSES.txt          # upstream licences + SolidCraft relationship
├── cordis.patch.yml                  # dsh: inserts the plugin into a profile
├── docs/
│   ├── ACKNOWLEDGEMENTS.md           # who reported what, and what it changed
│   ├── ACKNOWLEDGEMENTS_zh.md        # 同上，中文
│   ├── BLENDER_SKILLS.md             # the 30 bundled skills, with what each covers
│   ├── BLENDER_SKILLS_zh.md          # 同上，中文
│   ├── DEPENDENCIES.md               # capability / dependency / missing-behaviour matrix
│   ├── INSTALL_COMMANDS.md           # every host's install command, every install.py flag
│   ├── INSTALL_COMMANDS_zh.md        # the same, in Chinese
│   ├── REFERENCE.md                  # this file
│   ├── REFERENCE_zh.md               # 同上，中文
│   ├── THIRD_PARTY.md                # the vendored SolidCraft references and their licence
│   └── THIRD_PARTY_zh.md             # 同上，中文
├── examples/
│   ├── bracket_request.json          # natural language + 21 SolidCraft commands
│   ├── damaged_part.stl              # holed sphere for inspect / repair demos
│   └── make_demo.py                  # regenerates damaged_part.stl
├── index.js                          # dsh entry: registers every skills/*/SKILL.md
├── install.py                        # --check / --deps / --skill-dir / --project / --global
├── licenses/
│   └── cc-blender-skill-LICENSE.txt  # upstream MIT text for the bundled skills
├── manifest.json                     # skill-pipeline metadata (stage, actions, deps)
├── package.json                      # package manifest; `files` decides what ships
├── pyproject.toml                    # package metadata + pytest/pyright config
├── requirements.txt
├── references/
│   └── solidcraft/                   # SolidCraft's four agent references, verbatim (MIT)
│                                     #   README.md: provenance, hashes, update steps
├── run.py                            # CLI: probe / model / script / measure /
│                                     #      snapshot / inspect / repair
├── scripts/
│   ├── engine.py                     # trimesh geometry: load, transform, analyze, repair, export
│   └── solidcraft.py                 # CLI bridge: probe, run, eval, snapshot, script
├── skills/
│   ├── vendored.json                 # upstream URL, fetch date, SHA-256 per skill file
│   ├── 3d-fabric/                    # this plugin's own skill: CAD half + routing
│   └── <30 Blender skills>/          # verbatim from github.com/RobLe3/cc-blender-skill
│                                     #   (MIT): 11 production + 2 HUD/animation QA
│                                     #   + 17 reference-reconstruction skills
└── tests/                            # development only — excluded from `package.json` files
    ├── conftest.py                   # generated fixtures (no binary blobs)
    ├── stub_solidcraft.py            # test double for the CLI
    ├── test_actions.py               # measure / snapshot / script, model --in
    ├── test_bundled_skills.py        # Blender skills present, bound to an MCP, hashes match
    ├── test_cli.py                   # exit codes, gate files, stdout contract
    ├── test_dsh_bundle.py            # dsh.bundle.patch, the CJS entry, version agreement
    ├── test_engine.py                # geometry, defects, repair, export
    ├── test_install.py               # --check, --skill-dir, argument handling
    ├── test_model.py                 # the full build → inspect chain
    ├── test_plugin_manifests.py      # four plugin manifests + six rule files stay in step
    ├── test_references.py            # SolidCraft references present, hashes match
    └── test_solidcraft.py            # probe, run, failure and silent-success cases
```

## Tests

```bash
python -m pytest
```

138 tests. They cover the geometry engine (loading STL with welding, transforms about a pivot,
winding, inverted shells, cavities versus inside-out bodies, every defect class, hole filling on quads
and on a 32-gon boundary, export round-trips against an independent STL reader), the CLI contract
(exit codes, gate files, human and `--json` output), the design-reading actions (`measure` totals and
open bodies, `snapshot` PNG output, `script` extraction, `model --in`), the bundled references
(presence, provenance hashes against the README table, the MIT text, and that `install.py --skill-dir`
copies them), the bundled Blender skills (present, named by their frontmatter, every one bound to a
Blender MCP tool set, cross-skill links resolving, hashes matching `skills/vendored.json`), the dsh
package (the `dsh.bundle.patch` declaration, the CJS entry listing all thirty-one skills, version
agreement with the Claude Code manifests), the platform half (all four plugin manifests and all six
rule files, each rule file pinned to `AGENTS.md` so one edit cannot leave a host behind), the
installer's own checks, and the SolidCraft bridge through a Python stub CLI — so the suite passes on a
machine with SolidCraft installed or not. When the real CLI is present, one integration test runs
against it and is skipped otherwise.

The suite is part of the repository but not of the package: `package.json` lists what ships, and
`tests/` is not in it.
