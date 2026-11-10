# Dependency matrix

`3d-fabric` starts with Python's standard library plus three runtime packages.
SolidCraft is an external program, not a Python package, and either half of the
mesh pipeline degrades with a clear message rather than a traceback.

| Capability | Needs | Licence | Required? | Missing behaviour |
|---|---|---|---|---|
| `inspect`, `repair` — load, analyse, export a mesh | `trimesh` + `numpy` | MIT / BSD-3-Clause | yes | `ImportError` naming the package and the install command |
| Boundary-loop connected components during `repair` | `scipy` | BSD-3-Clause | yes | same import error; no silent fallback |
| `model`, `script`, `measure`, `snapshot` | `solidcraft-cli` | MIT OR Apache-2.0 | yes for those four | `probe` reports `UNVERIFIED` with an install hint; the action exits non-zero and never reports success |
| `snapshot` rendering | SolidCraft's own renderer (GPU or CPU) | — | yes for that action | SolidCraft reports the failure; `snapshot` passes it through unchanged |
| Every action | Python 3.10+ | PSF-2.0 | yes | `install.py --check` reports the interpreter it found |
| Test suite cross-check of exported STL | `numpy-stl` | BSD-3-Clause | no | that test is skipped |
| Test suite | `pytest` | MIT | no | `python -m pytest` reports the missing module |

Install the required set:

```bash
pip install -r requirements.txt
```

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
