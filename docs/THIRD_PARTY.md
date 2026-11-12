# Bundled third-party material

`references/solidcraft/` holds the four agent reference documents SolidCraft publishes for its own MCP server — **modeling**, **editing**, **checking** and **mechanisms** — together with the small helper scripts and design template that ship beside `solidcraft-checking`. The plugin's skill reads them for command shapes, plane axes, ids, reply sizes and the traps that make a build succeed with the wrong geometry.

**English** · [简体中文](THIRD_PARTY_zh.md)

## What this is, precisely

- **Verbatim, minus upstream's own tests.** Every file is byte-identical to upstream `github.com/tangency-labs/solidcraft` at branch `main` (fetched 2026-11-06); nothing was rewritten or merged. The one omission is `scripts/tests/` — 829 lines of upstream's tests for its helper scripts, which nothing here runs.
- **Reference text, not skills.** Their YAML frontmatter is part of the upstream file. Nothing in that folder is registered as a Claude Code skill, and `run.py` never executes any of it.
- **MIT, with the notice kept.** SolidCraft is dual-licensed MIT OR Apache-2.0; this copy is taken under **MIT**. Copyright (c) 2026 SolidCraft contributors. [`LICENSE-MIT`](../references/solidcraft/LICENSE-MIT) carries the full MIT text and [`NOTICE`](../references/solidcraft/NOTICE) the upstream attribution. Those files remain the contributors' copyright and are not covered by 3d-fabric's own MIT grant; everything outside `references/solidcraft/` is Jiaming Shi's work under MIT.
- **Optional.** Delete the folder and `run.py` still works — you only lose the built-in command reference and fall back to `solidcraft-cli commands`.

## MCP names are not CLI names

The upstream text is written against SolidCraft's MCP tool names (`batch`, `execute`, `measure`). The command names inside `{"commands": [...]}` are the same ones; the MCP call names are not accepted by `solidcraft-cli run`. Where the two disagree, `solidcraft-cli commands` wins.

## Provenance

Per-file SHA-256 values, the fetch date and the update steps are in [`references/solidcraft/README.md`](../references/solidcraft/README.md). `tests/test_references.py` fails if a file and its hash disagree, so the table cannot drift silently.
