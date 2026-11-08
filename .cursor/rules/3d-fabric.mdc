---
description: 3d-fabric agent operating rules (v1.0.0)
alwaysApply: true
---

# 3d-fabric — agent operating rules (v1.0.0)

3d-fabric is the **whole 3D toolchain for this machine in one plugin**: build a
part by natural language through SolidCraft, read and edit a design someone
already made, measure it, render it, check any mesh for printing, and repair
meshes that came from elsewhere. It does not generate geometry itself and it
speaks to no CAD application other than SolidCraft.

It does not do organic modelling, sculpting, materials, lighting or animation.

## Install as one plugin

Install this repository as a **single plugin**. Do NOT copy `run.py` on its own
— it imports `scripts/engine.py` and `scripts/solidcraft.py`, and the skill
lives at `skills/3d-fabric/SKILL.md`. Use the marketplace, or let
`install.py --skill-dir` perform the copy.

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
