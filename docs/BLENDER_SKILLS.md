# The Blender half — 30 bundled skills

Thirty skills ship in `skills/`, copied verbatim from [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill) at commit `a2634b5` (MIT). Each declares its Blender MCP tools in `allowed-tools`, so it activates only where a Blender MCP server is connected.

**English** · [简体中文](BLENDER_SKILLS_zh.md)

**What this half needs:** Blender installed on the machine, and one Blender MCP server connected (`mcp__blender__*` from ahujasid/blender-mcp, or `mcp__blender_official__*`). Without them the CAD half still runs; these skills say what is missing instead of describing a render they did not make.

## Production (11 skills)

| Skill | Covers |
| --- | --- |
| `text-to-blender` | the router: picks the right sub-skill, the MCP backend guide, assembly order |
| `blender-modeling` | meshes, primitives, modifiers, bmesh, hard-surface work |
| `blender-materials` | Principled BSDF, metallic switch, coat/sheen/SSS/transmission, procedural patterns |
| `blender-lighting` | three-point setups, HDRI, colour temperature, light groups |
| `blender-cameras` | focal length, depth of field, composition, animated cameras |
| `blender-rendering` | Cycles vs EEVEE, samples, denoising, AgX/Filmic, output formats |
| `blender-animation` | keyframes, F-curves, easing, shape keys, drivers, NLA |
| `blender-export` | glTF/GLB, FBX, OBJ, USD, STL, collision hulls, normal baking |
| `blender-uv-texturing` | unwrap, atlas mapping, projection, baking, decals |
| `blender-pro-workflow` | the order to assemble a scene, critique protocol, time budgets |
| `blender-skill-harmonizer` | precedence and handoffs when several of the above apply |

## HUD and animation QA (2 skills)

| Skill | Covers |
| --- | --- |
| `orbital-hud-motion` | circular HUD, aura rings, orbit arcs around a subject |
| `animation-quality-gate` | contact sheets, flicker and silhouette checks before accepting a pass |

## Reference reconstruction (17 skills)

The family that makes "match this sheet exactly" possible:

| Skill | Covers |
| --- | --- |
| `reference-to-3d` | rebuild from reference sheets, orthographic views, brand or mascot art |
| `wireframe-to-3d` | orthographic wireframe drawings → model, exported as glTF/GLB |
| `mascot-logo-reconstruction` | fail-gated, source-locked mascot / logo / avatar rebuild |
| `orthographic-registration` | register front/side/back/top views into one coordinate contract |
| `multiview-constraint-solver` | decide whether one rigid model can satisfy every view; emit constraints (no Blender tool needed) |
| `multiview-fit-loop` | compare-adjust-repeat fitting against the templates |
| `fit-repair-optimizer` | turn fit reports into a repair queue |
| `landmark-fit-repair` | repair against named landmarks (tips, corners, eyes, rim thickness) |
| `reference-analysis-validator` | validate the supplied references before calling a rebuild 1:1 |
| `reference-look-calibration` | calibrate materials, light, crop, glow and HUD styling against the original |
| `source-part-segmentation` | plan how a reference splits into parts (no Blender tool needed) |
| `contour-to-mesh` | build surfaces from extracted contours and masks |
| `atlas-uv-fitting` | map each source part to its own atlas rectangle |
| `closed-surface-uv-coverage` | cover caps and sidewalls of closed or extruded assets |
| `texture-driven-mesh-fitting` | reshape geometry to texture or decal contours |
| `texture-state-animation` | texture-state transitions without crossfades or popping |
| `quality-refinement-autoloop` | self-refine when a result misses the bar |

## Not edited here

They are upstream text; routing and local advice live in `skills/3d-fabric/SKILL.md` and `AGENTS.md`. `skills/vendored.json` records the upstream commit date and a SHA-256 per file, and `tests/test_bundled_skills.py` fails if a file and its hash disagree.

A Blender mesh reaches the printer the same way any other mesh does: export STL, then `run.py --action inspect` and `repair`.
