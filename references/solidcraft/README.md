# SolidCraft agent references (vendored, unmodified)

These four documents are the SolidCraft project's own agent skills. They are
copied here **verbatim** so that `skills/3d-fabric/SKILL.md` can read the
command shapes, plane axes, ids, reply sizes and known traps without requiring a
second, separately installed set of skills on the machine.

They are reference text, not Claude Code skills: nothing here is registered as a
skill, the YAML frontmatter is kept only because it is part of the upstream file,
and the host agent never triggers on them.

## Provenance

| | |
| --- | --- |
| Upstream | <https://github.com/tangency-labs/solidcraft> |
| Path | `skills/<name>/` for each of the four names below |
| Branch | `main` |
| Fetched | 2026-11-06 |
| Modification | upstream's `scripts/tests/` is not copied; every other file is byte-identical (LF endings) |
| Licence of this copy | MIT, per upstream's `MIT OR Apache-2.0` dual licence |

The local copies in `~/.claude/skills/solidcraft-*` (if present) are the same
files with CRLF endings; the copies here are the upstream LF bytes.

## Licence and attribution

SolidCraft is Copyright (c) 2026 SolidCraft contributors and is dual-licensed
under the MIT License or the Apache License, Version 2.0. This copy is taken
under **MIT**:

- [`LICENSE-MIT`](LICENSE-MIT) — the upstream MIT licence text, including the
  copyright notice, kept as MIT requires.
- [`NOTICE`](NOTICE) — the upstream NOTICE file, kept so the attribution that
  ships with SolidCraft travels with these files.

3d-fabric itself is MIT (see the repository `LICENSE`). Nothing in this folder
is covered by 3d-fabric's copyright; it remains SolidCraft contributors' work.

## Files

| Upstream path | SHA-256 |
| --- | --- |
| `skills/solidcraft-modeling/SKILL.md` | `b8e1ae5ce84186306f33a58d5b51e1c662c855afe073977911ea833a2be298d3` |
| `skills/solidcraft-modeling/reference.md` | `e604f098819476154d1519582e1176976205b8628a1afb7b52bc4799ba9f18c6` |
| `skills/solidcraft-editing/SKILL.md` | `d8730bbed1c0dd8de8c8602f545c694fd6d78fabad90d864da89f614794ce195` |
| `skills/solidcraft-mechanisms/SKILL.md` | `cc7320809f96c9a8094529b61a87f1e6802141684d07c3b18883aa3cf59eb790` |
| `skills/solidcraft-mechanisms/reference.md` | `4165a949715731e503804158225c5f1b02e1c5233c330c0e2fe47bb0d959785f` |
| `skills/solidcraft-checking/SKILL.md` | `e9806026a201d391286c4c4a6cab094629ba2c82a81a368f041b2210f48545be` |
| `skills/solidcraft-checking/reference/porting.md` | `c2614bcbacd5811bb3a7dcd2e0ee984ba2d61f79d07cb4e477b4f301fc0c88d0` |
| `skills/solidcraft-checking/scripts/compare_step.py` | `ef4d3dcb1993131ad1a72cdc5a013eb17b131ecce8337d23e0f76f2ded74e82d` |
| `skills/solidcraft-checking/scripts/run.py` | `40ac7535bbe1058e7ab46764fc8622c9c7ab10fc087b6d3678f349921c170c0e` |
| `skills/solidcraft-checking/scripts/scb.py` | `e9e64305bf44a3fe0c93bb74457f6b4118b2c6dc3383adddd4addeafb85fcb61` |
| `skills/solidcraft-checking/templates/test_design.py` | `9a01f3970d596977853c178a751abcf2490d28df7c16217421595300a75cfe4f` |
| `LICENSE-MIT` | `1a26c1e94401d5d221896c74dd1c58d227edc64516da95aaac6f675567c8af63` |
| `NOTICE` | `09464b0c8f495c9e3c80d93fccf667056d1c2c306445d66101e4bed49494c54d` |

## What is not copied

Upstream's own test suite — `solidcraft-checking/scripts/tests/`, four files, 829 lines — is
left out. It exercises SolidCraft's helper scripts against a live `solidcraft-cli` with
`build123d` installed; nothing in 3d-fabric runs it, and 3d-fabric's own suite never
collects it. The paragraph in `solidcraft-checking/SKILL.md` that tells you to run
`$SKILL/scripts/tests` after a SolidCraft upgrade therefore does not apply to this copy;
everything else in that file is upstream text unchanged.

## What each one is for

- **solidcraft-modeling** — building a new part: parameter/sketch/feature shapes,
  plane axes, edge and face ids, reply sizes, and the traps that make a build
  succeed with the wrong geometry. Start with `reference.md`.
- **solidcraft-editing** — changing an existing design through its parameters
  (`d1`, `d2`, …), mapping a design in three or four calls, and when
  `timeline.inspect` is worth it.
- **solidcraft-checking** — the errors SolidCraft does not report (parameter
  ranges, allowed values), exact STEP comparison, regression tests, porting from
  build123d / CadQuery / OpenSCAD.
- **solidcraft-mechanisms** — assemblies, joints, motion links and closed loops.
  The `run.py` actions here drive single parts, so this one is background only.

The upstream text is written for SolidCraft's MCP server (`batch`, `execute`,
`measure`). The command names are the same ones a `{"commands": [...]}` script
uses; the MCP call names are not accepted by `solidcraft-cli run`.

## Updating

```bash
base=https://raw.githubusercontent.com/tangency-labs/solidcraft/main/skills
curl -fsSL "$base/solidcraft-modeling/reference.md" -o solidcraft-modeling/reference.md
```

Fetch each path in the table, confirm the numbers in `SKILL.md` still match the
installed CLI (`solidcraft-cli commands`), then refresh the hashes above. Keep
the files verbatim; put any 3d-fabric-specific advice in
`skills/3d-fabric/SKILL.md` instead.
