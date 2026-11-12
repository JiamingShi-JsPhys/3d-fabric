# 致谢

报告了问题、并因此改变了本项目的人；这里写他们报了什么、改了什么。README 只留名字，细节在这一页。

[English](ACKNOWLEDGEMENTS.md) · **简体中文**

## wlheyuyang

[issue #1](https://github.com/JiamingShi-JsPhys/3d-fabric/issues/1)。

一个水密立方体只要有一个三角形方向反了，也会被判成 `ready_to_print`。`inconsistent_winding` 当时只是
`warning`，于是 `trimesh` 已经报 `is_volume = False` 的表面照样过门——切片软件只能去猜那个三角形的外侧
在哪一边。该 issue 提供了复现方法。

1.1.1 把这条改成 `error`，并且对任何「水密但不是体积」的网格拒绝给出 `ready_to_print`；判定停在
`needs_repair` 且 `repairable: true`，因为 `repair` 本来就能用 `fix_normals` 修好它。
