# Dependency matrix

`3d-fabric` starts with Python's standard library plus five runtime packages.
SolidCraft is an external program, not a Python package, and either half of the
mesh pipeline degrades with a clear message rather than a traceback.

| Capability | Needs | Licence | Required? | Missing behaviour |
|---|---|---|---|---|
| `inspect`, `repair` — load, analyse, export a mesh | `trimesh` + `numpy` | MIT / BSD-3-Clause | yes | `ImportError` naming the package and the install command |
| Boundary-loop connected components during `repair` | `scipy` | BSD-3-Clause | yes | same import error; no silent fallback |
| Hole filling, through `trimesh.repair` | `networkx` | BSD-3-Clause | yes | `repair` without `--no-fill-holes` fails with `No module named 'networkx'` |
| `.3mf` export, through `trimesh.exchange.threemf` | `lxml` | BSD-3-Clause | yes | `.3mf` export fails with `No module named 'lxml'`; STL, OBJ and STEP still work |
| `model`, `script`, `measure`, `snapshot` | `solidcraft-cli` | MIT OR Apache-2.0 | yes for those four | `probe` reports `UNVERIFIED` with an install hint; the action exits non-zero and never reports success |
| the twelve image-processing skills (`wireframe-to-3d`, `reference-to-3d`, `contour-to-mesh`, `source-part-segmentation`, …) | `opencv-python`, `Pillow`, `scikit-image` | Apache-2.0 / MIT-CMU / BSD-3-Clause | no for the seven actions, yes for those skills | the script stops with `No module named 'cv2'` (or `PIL`, `skimage`); `install.py --check` lists them under `skill extras` and still reports the plugin ready |
| the thirty Blender skills | a local Blender **and** a Blender MCP server (`mcp__blender__*` / `mcp__blender_official__*`) | Blender: GPL-3.0 (separate program, called over MCP) | yes for those skills | the skill says Blender is missing; it never describes a render it did not make. `run.py` never touches Blender |
| `snapshot` rendering | SolidCraft's own renderer (GPU or CPU) | — | yes for that action | SolidCraft reports the failure; `snapshot` passes it through unchanged |
| Every action | Python 3.10+ | PSF-2.0 | yes | `install.py --check` reports the interpreter it found |
| Test suite cross-check of exported STL | `numpy-stl` | BSD-3-Clause | no | that test is skipped |
| Test suite | `pytest` | MIT | no | `python -m pytest` reports the missing module |

Install the required set:

```bash
pip install -r requirements.txt
```

Enable the skill extras — the twelve skills that read or write images:

```bash
pip install "3d-fabric[skills]"     # opencv-python, Pillow, scikit-image
```

The seven `run.py` actions never import them, so a machine that only inspects
and repairs meshes does not need them, and `install.py --check` prints them as
`OPT` rather than `MISS`.

Enable the test extras:

```bash
pip install pytest numpy-stl
```

SolidCraft is not a Python dependency and is not vendored. Download it from
[the downloads page](https://solidcraft.io/download) — Windows `.msi`, macOS
`.dmg`, Linux AppImage or `snap` — and verify with `solidcraft-cli --version`.
Per-platform links, the `PATH` fallback and the `SOLIDCRAFT_CLI` /
`SOLIDCRAFT_HOME` overrides are in [INSTALL_COMMANDS.md](INSTALL_COMMANDS.md).

`inspect` and `repair` work with no SolidCraft at all: a mesh from a scanner, a
download or another CAD package stays checkable on a machine that has never
installed a CAD application.

No GPL or AGPL package is used. See
[`THIRD_PARTY_LICENSES.txt`](../THIRD_PARTY_LICENSES.txt).
