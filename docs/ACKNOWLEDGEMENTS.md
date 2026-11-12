# Acknowledgements

People who reported a problem that changed this project, with what they reported and what it changed. The README carries the name; this page carries the detail.

**English** · [简体中文](ACKNOWLEDGEMENTS_zh.md)

## wlheyuyang

[issue #1](https://github.com/JiamingShi-JsPhys/3d-fabric/issues/1).

A watertight cube with one reversed triangle came back `ready_to_print`. `inconsistent_winding` was registered as a `warning`, so a surface that `trimesh` already reported as `is_volume = False` still passed the gate — and a slicer would have had to guess which side of that triangle is outside. The issue supplied the reproduction.

1.1.1 makes the code an `error`, refuses `ready_to_print` for any watertight mesh that is not a volume, and keeps the verdict at `needs_repair` with `repairable: true` because `repair` already fixed it through `fix_normals`.
