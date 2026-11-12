# Changelog

All notable changes to 3d-fabric are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] — 2026-11-06

The Blender half. 3d-fabric stops being only a CAD front end: it now ships the
thirty Blender skills that cover organic modelling, materials, lighting,
cameras, rendering, UV texturing, animation and animation QA, so one plugin
covers both kinds of 3D work.

### Added

- **Thirty skills in `skills/`** — the complete upstream set — verbatim from
  [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill)
  (`plugin/skills/`, branch `main`, fetched 2026-11-06, MIT):
  - production (11): `text-to-blender` (the router), `blender-modeling`,
    `blender-materials`, `blender-lighting`, `blender-cameras`,
    `blender-rendering`, `blender-animation`, `blender-export`,
    `blender-uv-texturing`, `blender-pro-workflow`, `blender-skill-harmonizer`
  - HUD and animation QA (2): `orbital-hud-motion`, `animation-quality-gate`
  - reference reconstruction (17): `reference-to-3d`, `wireframe-to-3d`,
    `mascot-logo-reconstruction`, `orthographic-registration`,
    `multiview-constraint-solver`, `multiview-fit-loop`, `fit-repair-optimizer`,
    `landmark-fit-repair`, `reference-analysis-validator`,
    `reference-look-calibration`, `source-part-segmentation`,
    `contour-to-mesh`, `atlas-uv-fitting`, `closed-surface-uv-coverage`,
    `texture-driven-mesh-fitting`, `texture-state-animation`,
    `quality-refinement-autoloop`
- Because the reconstruction family now sits beside `text-to-blender` inside
  the plugin, their `../text-to-blender/references/mcp-backends.md` links
  resolve within the bundle; the standalone copies and the shared-folder
  workaround they needed can go.
- `skills/vendored.json` — upstream URL, fetch date, licence and a SHA-256 for
  each of the 131 bundled files, so drift is detectable.
- `licenses/cc-blender-skill-LICENSE.txt` — upstream MIT text, copyright
  © 2026 RobLe3, shipped with the skills as MIT requires.
- A routing table in `skills/3d-fabric/SKILL.md` and `AGENTS.md`: printable or
  parameterised work goes through `run.py`; silhouette, surface or motion work
  goes to the Blender skills. A Blender mesh reaches the printer only through
  `run.py --action inspect` / `repair` on an exported STL.

### Added — the platform half

One repository, ten hosts. The layout follows the pattern `chelate-shell` uses,
so both repositories install the same way.

- **Plugin manifests for the three other hosts that read one.**
  `.codex-plugin/` and `.codebuddy-plugin/` each ship `plugin.json` plus
  `marketplace.json`; `.dsh-plugin/` ships a `plugin.json` and a CJS entry that
  delegates to the root `index.js` rather than keeping a second copy that could
  drift. `author` is an object in all four manifests, none carries a string
  `skills` field or an `icon` — the shapes that make these hosts drop a plugin
  without printing an error.
- **A rule file for every host that reads one instead of a plugin.**
  `.cursor/rules/3d-fabric.mdc` (`alwaysApply`), `.continue/rules/3d-fabric.md`
  (`alwaysApply`), `.windsurf/rules/3d-fabric.md` (`trigger: always_on`),
  `.roo/rules/3d-fabric.md`, `.clinerules/3d-fabric.md` and
  `.github/copilot-instructions.md`. Every one is `AGENTS.md` verbatim behind
  that host's header, so one edit to the contract reaches all six.
- **`install.py --project DIR` / `--global` / `--list` / `--only`** — the one
  command no vendor ships, because no host's installer understands another
  host's rule file. `--global` covers the user-scoped `AGENTS.md` for opencode
  and Codex, skipping a host this machine does not have; Claude Code is
  excluded there on purpose, since it has a plugin channel and
  `~/.claude/CLAUDE.md` belongs to the user. An identical file reports
  `unchanged`; a differing one is left alone unless `--force` is passed.
- `package.json` declares the version it ships, so the dsh package and the
  Claude Code manifests agree.

### Changed

- Version 1.1.0 across `plugin.json`, `marketplace.json`, `manifest.json`,
  `pyproject.toml` and the skill frontmatter; `manifest.json` also records
  `bundled_skills` and a `blender_requirement` block.
- The `3d-fabric` skill description now says it is **not** for organic or
  artistic modelling, so it stops competing with the Blender triggers.
- READMEs describe the two halves, the Blender requirements, the licence
  boundary and every host's install command; `THIRD_PARTY_LICENSES.txt` gains
  the cc-blender-skill entry. Marketplace commands pin `#v1.1.0`.
- `install.py --skill-dir` is unchanged: it installs the CAD skill and its
  references. The Blender skills are available through the plugin channel,
  where their per-skill `allowed-tools` are honoured.

### Unchanged

- `run.py` and `scripts/` are byte-identical to 1.0.0: same seven actions, same
  gate schema, same exit codes. A machine with no Blender behaves exactly as
  before.

### Tests

- 124 tests. `tests/test_bundled_skills.py` (8) covers the Blender half — all
  thirty skills present, frontmatter name matching the directory, every skill
  bound to a Blender MCP tool set, cross-skill relative links resolving inside
  the bundle, hashes matching `skills/vendored.json`, the MIT text present, and
  the CAD skill routing to the Blender half. `tests/test_dsh_bundle.py` (5)
  and the new `tests/test_plugin_manifests.py` (11) cover the platform half —
  the `dsh.bundle.patch` declaration, the CJS entry listing all thirty-one
  skills, version agreement across the four manifests and `package.json`, the
  two fields that get a plugin silently ignored, and every rule file still
  equalling `AGENTS.md`.

## [1.0.0] — 2026-11-08

First release. The complete 3D modelling and 3D-printing toolchain for one
machine, in one plugin: a natural-language front end for a local SolidCraft
installation, the tools that read and edit an existing design, and the
3D-printing quality gate that follows all of them — packaged so that ten agent
hosts can install it, four through a plugin manifest and six through a rule
file.

### Seven actions

- **`probe`** — locates `solidcraft-cli` through `--solidcraft`,
  `SOLIDCRAFT_CLI`, `SOLIDCRAFT_HOME`, `PATH` and the vendor's default install
  folders, and accepts a candidate only after it answers `--version` with exit
  code 0, so a stale shim on `PATH` cannot pass as a working install.
- **`model`** — runs an agent-written `{"commands": [...]}` script or `.sc`
  design headlessly, exports STL / STEP / 3MF / OBJ by extension, and inspects
  the result inside the same gate. Keeps the executed script
  (`.solidcraft.json`) and an editable `.sc` beside the export. `--in design.sc`
  applies the script on top of an existing design (e.g. a
  `parameters.change` patch), leaving the original untouched.
- **`script`** — turns a `.sc` / `.step` back into a `{"commands": [...]}`
  script via `solidcraft-cli script`, so a design that arrived without its
  source can still be read, edited and replayed. SolidCraft's own replay note
  (for `timeline.add` steps) is carried into the gate's `notes`.
- **`measure`** — reads volume, surface area, mass (from the design's material
  density), bounds, closedness, face/edge/vertex counts, face types and every
  parameter out of the B-rep via `solidcraft-cli eval`. Reports per body plus
  totals; `PASS` only when every body is closed, `UNVERIFIED` otherwise.
- **`snapshot`** — renders a PNG preview via `solidcraft-cli snapshot`, with
  view selection (`--view`), section cuts (`--section`) and per-body styling
  (`--body NAME:opacity=…,color=#rrggbb`); the gate records path, byte count
  and image info.
- **`inspect`** — reports watertightness, winding consistency, normal
  orientation, non-manifold edge count, boundary loops, degenerate faces,
  bounds, surface area and signed volume, and reduces them to
  `ready_to_print` / `needs_repair` / `blocked`.
- **`repair`** — welds vertices, drops degenerate and duplicate faces, drops
  unreferenced vertices, fills single-face and ordered-loop holes, then fixes
  winding and inversion. Every step records what it changed.

### Bridge behaviour verified against SolidCraft 0.30.1

- **Exit code 1 means failure**, with `error: step N (cmd): ...` on stderr.
  The step index is 1-based and maps to the command list, so a failure points
  at the exact step to fix.
- **Exit code 0 does not mean a file was written.** `model` verifies every
  promised export exists and is non-empty and turns a silent run into `FAIL`.
- **`--out` exports by extension** and may be repeated; `--save` writes an
  editable `.sc`; `--results --json-out` yields the per-step list.
- **`eval --json-out`, `snapshot --out` and `script --out`** cover reading,
  previewing and recovering a design; all three were exercised against the
  real CLI before being wired in.
- **Tessellation quality is a per-command setting**, not a `run` flag, so
  `--quality fine|finest` injects `file.export_stl` into JSON scripts. `.sc`
  designs use the default and say so in `notes`.
- **`parameters.change`, not `set_parameter`.** The latter does not exist; the
  correct name is documented in the skill so an agent does not invent it.

### Deliberate design choices

- **`inspect` and `repair` do not require SolidCraft.** Meshes from a scanner,
  a download or another program stay checkable on a machine that has never
  installed a CAD application. Only the four SolidCraft-backed actions
  (`model`, `script`, `measure`, `snapshot`) hard-fail when the CLI is missing,
  with an explicit install message.
- **`repair` never claims success while a defect remains.** A non-manifold edge
  leaves `success: false` and its count in `after.topology`.
- **Hole filling is a planar fan.** A loop whose out-of-plane thickness exceeds
  5% of its radius is skipped with a note rather than filled badly.
- **Units are stated, not guessed.** STL carries none; the report says `mm` and
  marks it as an assumption.
- **One plugin instead of four.** Building, editing, measuring, previewing,
  verifying and repairing share one CLI, one gate schema and one set of exit
  codes, so a machine needs no separate modelling, audit or viewer skill.

### Bundled SolidCraft references (MIT)

- `references/solidcraft/` reproduces SolidCraft's four agent reference
  documents — modeling, editing, checking and mechanisms — verbatim from
  `github.com/tangency-labs/solidcraft` branch `main` (fetched 2026-11-06),
  together with the helper scripts and design template that ship beside
  `solidcraft-checking`.
- SolidCraft is dual-licensed MIT OR Apache-2.0; this copy is taken under
  **MIT**, with upstream's copyright notice, `LICENSE-MIT` and `NOTICE` kept
  beside the files, and per-file SHA-256 values in
  `references/solidcraft/README.md`. Those files remain SolidCraft
  contributors' copyright; the rest of the plugin remains MIT.
- They are reference text, not Claude Code skills: the frontmatter is upstream's
  own, nothing in the folder is registered as a skill, and `run.py` never
  executes it. Deleting the folder leaves the plugin working and only drops the
  built-in command reference.

### dsh packaging

- **The repository installs as a dsh (DeepSeek Harness) bundle.**
  `package.json` declares `dsh.bundle.patch`, `cordis.patch.yml` inserts the
  plugin, and `index.js` registers the skills under `skills/` with the
  session's skill registry, so the same `SKILL.md` files that Claude Code loads
  also reach a dsh session. It holds no runtime dependency: the frontmatter
  reader for folded scalars and invocation flags is part of the file.
- dsh refuses any package whose `package.json` lacks `dsh.bundle.patch` — the
  *"这个包没有声明组合包"* refusal, `reasonNotBundle` — so that field is not
  optional. `.dsh-plugin/` carries a second entry for hosts that look for a
  directory; it delegates to the root `index.js` rather than duplicating it.

### One repository, ten hosts

- **Plugin manifests for the three other hosts that read one.**
  `.codex-plugin/` and `.codebuddy-plugin/` each ship `plugin.json` plus
  `marketplace.json`; `author` is an object in all four manifests, and none
  carries a string `skills` field or an `icon` — the shapes that make these
  hosts drop a plugin without printing an error.
- **A rule file for every host that reads one instead of a plugin.**
  `.cursor/rules/3d-fabric.mdc` (`alwaysApply`), `.continue/rules/3d-fabric.md`
  (`alwaysApply`), `.windsurf/rules/3d-fabric.md` (`trigger: always_on`),
  `.roo/rules/3d-fabric.md`, `.clinerules/3d-fabric.md` and
  `.github/copilot-instructions.md`. Every one is `AGENTS.md` verbatim behind
  that host's header, so one edit to the contract reaches all six.
- **`install.py --project DIR` / `--global` / `--only` / `--list`** — the one
  command no vendor ships, because no host's installer understands another
  host's rule file. `--global` covers the user-scoped `AGENTS.md` for opencode
  and Codex, skipping a host this machine does not have; Claude Code is
  excluded there on purpose, since it has a plugin channel and
  `~/.claude/CLAUDE.md` belongs to the user. An identical file reports
  `unchanged`; a differing one is left alone unless `--force` is passed.

### Packaging

- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` for the
  Claude Code plugin channel; `manifest.json` for the skill pipeline.
- `skills/3d-fabric/SKILL.md` carries the host-agent contract: how to translate
  a request into SolidCraft commands, how to read an existing design, and how
  to read a failing step.
- `install.py` checks python / geometry stack / SolidCraft / examples, installs
  dependencies, and copies `run.py`, `scripts/`, `SKILL.md` and the `references/`
  tree together into a host skill directory.
- `AGENTS.md` short-form rules; `README.md` + `README_zh.md`; 100 tests, with
  the CLI bridge driven by a Python stub so the suite passes with or without
  SolidCraft installed.

### Clean room

Geometry is delegated to `trimesh` (MIT); no slicing-software code is used or
adapted. SolidCraft is called as an external program and is neither bundled nor
redistributed.

### Tests

116 tests. The geometry engine (loading STL with welding, transforms about a
pivot, every defect class, hole filling on quads and on a 32-gon boundary,
inverted shells, export round-trips against an independent STL reader), the CLI
contract, the design-reading actions, the bundled references and their hashes,
the installer, the dsh package (`dsh.bundle.patch`, the CJS entry, version
agreement with the Claude Code manifests), the platform layer (four manifests,
six rule files, each pinned to `AGENTS.md`), and the SolidCraft bridge through
a Python stub CLI — so the suite passes on a machine with SolidCraft installed
or not.
