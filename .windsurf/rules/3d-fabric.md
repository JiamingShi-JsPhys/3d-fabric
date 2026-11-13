---
trigger: always_on
description: 3d-fabric agent operating rules (v1.1.2)
---

# 3d-fabric — agent operating rules (v1.1.2)

3d-fabric is the **whole 3D toolchain for this machine in one plugin**, in two
halves. The **CAD half** builds a part by natural language through SolidCraft,
reads and edits a design someone already made, measures it, renders it, checks
any mesh for printing, and repairs meshes that came from elsewhere. The
**Blender half** ships thirty skills for organic modelling, materials,
lighting, cameras, rendering, UV and animation.

Pick the half by the job: a printable, dimensioned part is CAD; something with
a silhouette, a surface look or a moving shot is Blender.

## Install as one plugin

Install this repository as a **single plugin**. Do NOT copy `run.py` on its own
— it imports `scripts/engine.py` and `scripts/solidcraft.py`, and the skill
lives at `skills/3d-fabric/SKILL.md`. Use the marketplace, or let
`install.py --skill-dir` perform the copy.

`skills/` holds thirty-one skills: the CAD skill and the thirty Blender ones.
Hosts that read a **rule file** instead of a plugin — Cursor, Windsurf, Cline,
Continue, Roo Code, GitHub Copilot — get this same contract through
`python install.py --project <dir>`; `python install.py --list` shows every
destination. `.claude-plugin/`, `.codebuddy-plugin/`, `.codex-plugin/` and
`.dsh-plugin/` are the four plugin manifests; this file is the body all six
rule files carry.

## Entry points (Python 3.10+)

```bash
python run.py --action probe                       # is SolidCraft reachable?
python run.py --action model   --input req.json    # build + export + inspect
python run.py --action script  --input part.sc --output build.json
python run.py --action model   --script patch.json --in part.sc --output new.stl
python run.py --action measure --input part.sc
python run.py --action snapshot --input part.sc --output preview.png --view iso
python run.py --action inspect --input part.stl    # mesh gate only
python run.py --action repair  --input part.stl --output fixed.stl
```

## The seven actions

1. **probe** — locate the CLI (`--solidcraft`, `SOLIDCRAFT_CLI`,
   `SOLIDCRAFT_HOME`, `PATH`, known folders) and verify it with `--version`.
   A missing CLI is `UNVERIFIED`, never a crash.
2. **model** — run a `{"commands": [...]}` script or `.sc` design, export by
   extension, then inspect automatically. Keeps the executed script and an
   editable `.sc` beside the output. `--in design.sc` applies the script on top
   of an existing design; the original file is never modified.
3. **script** — turn a `.sc` / `.step` back into `{"commands": [...]}`, so a
   design that arrived without its script can still be read, edited and replayed.
4. **measure** — per-body volume, area, mass (from the design's material),
   bounds, closedness, face/edge/vertex counts, face types and all parameters.
   Answer "how heavy / how big" from this, not from the mesh.
5. **snapshot** — render a PNG preview: `--view iso|front|…`, `--section`,
   `--body NAME:opacity=…,color=#rrggbb`, `--width/--height`.
6. **inspect** — watertightness, winding, normals, non-manifold edges, boundary
   loops, degenerate faces, bounds, signed volume → `ready_to_print` /
   `needs_repair` / `blocked`.
7. **repair** — weld, drop bad faces, fill single-face and ordered-loop holes,
   fix winding and inversion. Only for meshes that came from elsewhere.

## The Blender half (30 skills)

`skills/text-to-blender` is the router for the other twenty-nine:

- production: `blender-modeling`, `blender-materials`, `blender-lighting`,
  `blender-cameras`, `blender-rendering`, `blender-animation`,
  `blender-export`, `blender-uv-texturing`, `blender-pro-workflow`,
  `blender-skill-harmonizer`
- HUD and animation QA: `orbital-hud-motion`, `animation-quality-gate`
- reference reconstruction: `reference-to-3d`, `wireframe-to-3d`,
  `mascot-logo-reconstruction`, `orthographic-registration`,
  `multiview-constraint-solver`, `multiview-fit-loop`, `fit-repair-optimizer`,
  `landmark-fit-repair`, `reference-analysis-validator`,
  `reference-look-calibration`, `source-part-segmentation`, `contour-to-mesh`,
  `atlas-uv-fitting`, `closed-surface-uv-coverage`,
  `texture-driven-mesh-fitting`, `texture-state-animation`,
  `quality-refinement-autoloop`

- They need a local Blender **and** a Blender MCP server
  (`mcp__blender__*` or `mcp__blender_official__*`). If neither tool set is
  present, say Blender is missing — never describe a render you did not make.
- Before the first Blender call, read
  `skills/text-to-blender/references/mcp-backends.md`; keep one backend for the
  whole task.
- They are upstream text (MIT, © 2026 RobLe3). Never edit them. Routing and
  local advice belong in `skills/3d-fabric/SKILL.md` and this file.
- The Blender half and the CAD half do not share state: a Blender mesh reaches
  the printer only through `run.py --action inspect/repair` on an exported STL.

## Where the command reference lives

`references/solidcraft/` bundles SolidCraft's four agent reference documents
(modeling, editing, checking, mechanisms) verbatim under their MIT licence. Read
`references/solidcraft/solidcraft-modeling/reference.md` before writing steps.
Never edit those files — they are upstream text; put local advice in
`skills/3d-fabric/SKILL.md` instead.

## Hard rules

- Do not invent SolidCraft command names. Check with
  `solidcraft-cli commands | grep <word>` before writing a step, and read the
  bundled `references/solidcraft/solidcraft-modeling/reference.md`.
- Change a parameter with `parameters.change` — `set_parameter` does not exist.
- A run that reports success may still have written nothing; `model` verifies
  the export and turns that into `FAIL`. Trust the gate, not the exit code.
- A cut that misses still returns success. Compare the reported `volume` with
  your own calculation.
- Treat `error: step N (cmd)` as: command N of the list (1-based), fix that
  one, re-run the whole script. SolidCraft is all-or-nothing.
- Never modify the user's original `.sc`; everything is written beside the
  output.
- Never present a STEP export as printable: it is a B-rep with no triangles.
- `inspect` and `repair` do not require SolidCraft. Do not refuse them when the
  CLI is absent.

Full skill contract: [skills/3d-fabric/SKILL.md](skills/3d-fabric/SKILL.md).
