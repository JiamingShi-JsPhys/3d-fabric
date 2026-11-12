---
name: 3d-fabric
version: 1.1.0
description: >
  The complete 3D modelling and 3D-printing toolchain for this machine: drive
  the installed SolidCraft CAD application by natural language, edit an
  existing design, measure it, render a preview, check the mesh for printing,
  and repair meshes that came from elsewhere. Use whenever the user asks for a
  3D model, a printable part, parametric CAD, an enclosure, bracket, plate,
  flange or fixture ("3D 打印", "参数化建模", "建一个实体模型", "做个外壳/支架"),
  or asks to open, change, measure, preview, check or repair a 3D model.
  Not for organic or artistic modelling, materials, lighting, rendering or
  animation — the thirty bundled Blender skills cover that half.
metadata:
  version: 1.1.0
  author: Jiaming Shi
  license: MIT
  entry_point: run.py
  python_requires: '>=3.10'
---

# 3d-fabric — 本机的 3D 建模与打印工具链

一个插件覆盖从"说一句话"到"能上打印机"的全部环节，全部经由本机 SolidCraft：

| 你想要 | 用哪个动作 |
|---|---|
| 从零建一个新零件 | `model` |
| 改一个已有设计的参数/特征 | `script` + `model --in` |
| 知道它多大、多重、多少面 | `measure` |
| 看一眼长什么样 | `snapshot` |
| 确认能不能打印 | `inspect`（`model` 会自动跑） |
| 修一个别人给的破模型 | `repair` |

从 1.1.0 起本插件分两半，同一台机器上各管一段：

| 你想要的 | 用哪一半 |
|---|---|
| 能打印的机械件、参数化 CAD、改已有设计、测量、预览、质检、修复 | 本技能：`run.py` 的七个动作，走 SolidCraft |
| 有机/艺术造型、材质、灯光、相机、渲染、动画、按参考图重建 | 随附的 30 个 Blender 技能：`text-to-blender`、`blender-*`、`orbital-hud-motion`、`animation-quality-gate` |

Blender 那一半需要本机装有 Blender 并配置 Blender MCP（`mcp__blender__*` 或
`mcp__blender_official__*`）。工具不在时不要假装能建模——直接说明缺 Blender
和 MCP，让用户装好再来。以插件方式安装时这 30 个技能随附在 `skills/` 下；若当前
只是单独安装的技能目录、旁边没有它们，就说明这台机器只装了 CAD 一半。
两半的共同点是"做出来还要能验"：CAD 靠 gate，Blender 靠渲染出来的图。

除此之外，参数化实体 CAD 的建模、修改、测量、预览、打印验证与修复，这里都有。

本插件不实现实体核。SolidCraft 需用户自行安装（开源的参数化 CAD，
<https://github.com/tangency-labs/solidcraft>，MIT / Apache-2.0 双许可）。
本插件是面向它的第三方插件，与该项目无隶属关系。`references/solidcraft/` 下
收录了 SolidCraft 自己的四份 Agent 参考（逐字未改，MIT，附版权与 NOTICE，
见该目录 `README.md`）；除此之外不含其源码。

命令统一写作 `python "${CLAUDE_PLUGIN_ROOT:-.}/run.py"`：作为插件安装时宿主注入该变量；
作为普通技能安装在技能目录时，它回退到当前目录，`run.py` 就在旁边。

## 触发条件

- “3D 打印”“打印一个…”“做个能打印的…”
- “参数化建模”“建一个实体模型”“画一个零件”
- “外壳 / 支架 / 底板 / 法兰 / 安装板 / 夹具 / 转接件”
- “把这个零件改成…”“宽度改成 90”“加个孔”
- “这个模型多大/多重”“出张图看看”
- “检查这个 STL 能不能打印”“修一下这个模型的破洞”

不要把 CAD 流程用在：切片与 G-code、支撑、壁厚/悬垂分析——本插件不做切片。
有机造型、雕刻、材质、灯光、渲染与动画交给随附的 Blender 技能，不要用
`solid.extrude` 硬凑一个"艺术品"。

## 第 0 步：先探测（每次都要）

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action probe
```

未安装时直接返回：

> 请先在本机安装 SolidCraft 软件并配置环境变量，才能使用自然语言建模功能。

此时不要伪造结果，把这句话原样转述给用户并停止。已验证的安装位置会自动发现
（`PATH`、`%LOCALAPPDATA%\Programs\SolidCraft`、`D:/Applications/SolidCraft` 等）。
`inspect` 与 `repair` 不需要 SolidCraft，未安装照常可用。

## 第 1 步：把需求写成 SolidCraft 脚本

脚本是 JSON 命令列表：

```json
{"commands": [
  {"command": "parameters.add", "params": {"name": "L", "expression": "80 mm"}},
  {"command": "sketch.create", "params": {"plane": "XY", "name": "S1"}},
  {"command": "sketch.draw.dimensioned",
   "params": {"command": "sketch.rectangle.center",
              "params": {"center": [0, 0], "corner": [40, 25]},
              "dimensions": {"width": "L", "height": "50"}}},
  {"command": "sketch.finish", "params": {}},
  {"command": "solid.extrude", "params": {"distance": "6", "name": "Plate"}}
]}
```

**写命令前必须查证，不要凭记忆拼命令名**：

```bash
solidcraft-cli commands | grep -i param
```

SolidCraft 官方的 Agent 参考已经随本插件打包（原文逐字收录，MIT），直接读，
不用再依赖机器上另外装的那套技能：

| 需要什么 | 读这里 |
|---|---|
| 命令形状、平面轴、id、回复大小、已知陷阱 | `references/solidcraft/solidcraft-modeling/reference.md` |
| 改已有设计（参数 `d1`/`d2`、何时用 `timeline.inspect`） | `references/solidcraft/solidcraft-editing/SKILL.md` |
| SolidCraft 不报错的错误、STEP 精确比对、从其他 CAD 移植 | `references/solidcraft/solidcraft-checking/SKILL.md` |
| 装配、关节、运动副（本插件的单件流程用不到） | `references/solidcraft/solidcraft-mechanisms/` |

路径相对本技能目录（即 `run.py` 所在目录）。这些文档按 MCP 工具名书写
（`batch`、`execute`、`measure`），命令名与脚本里的 `command` 相同，但 MCP 的
调用名 `solidcraft-cli run` 不认；两者冲突时以 `commands` 输出为准并说明。

已知要点：

- 长度单位 mm，可写 `"16 in"`；数值字段可写表达式 `"w/2 - wall - 6"`。
- 草图平面 `XY`/`XZ`/`YZ`；`XZ` 上草图 y 轴对应世界 **-Z**。
- 拉伸默认吃**所有**区域，同心圆自动变成环——要实体盘就选 `profiles`。
- 改参数用 `parameters.change`（**不是** `set_parameter`，后者不存在）。
- **切割和孔没切中也会返回成功**：切开后必须拿 `volume` 与你算的值对一遍。
- 布尔收紧的步骤单独成批；参数化优先，能写表达式就别写死数字。

## 第 2 步：建模（新建或改已有）

**新建：**

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action model --input bracket_request.json --quality fine --json
```

需求 JSON 可同时携带自然语言与脚本：

```json
{"prompt": "一块 120x70x8 的转接板…", "commands": [ ... ],
 "output": "bracket.stl", "quality": "fine"}
```

**改已有设计**（脚本叠加在已有 `.sc` 上执行）：

```json
{"commands": [{"command": "parameters.change",
               "params": {"name": "L", "expression": "150 mm"}}]}
```

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action model --script widen.json \
    --in bracket.sc --output bracket_150.stl --json
```

常用参数：`--output`（扩展名决定格式 stl/step/3mf/obj）、`--quality`、
`--save-design` / `--no-save-design`、`--timeout`、
`--scale/--scale-xyz/--translate/--rotate/--center`（导出后变换网格并重新落盘）。

`model` **自动串联质检**：跑完 SolidCraft 后立刻体检导出的网格，一个 gate 返回全部结果。

## 第 3 步：读结果、闭环

```json
{"skill":"3d-fabric","status":"PASS","evidence_level":"EMPIRICAL","reason":"...",
 "data":{"probe":{...},"prompt":"...","script":"...",
         "solidcraft":{"returncode":0,"warnings":[],"step_count":17},
         "inspection":{"topology":{...},"printability":{"verdict":"ready_to_print",...}}}}
```

| status | 含义 | 你要做的 |
| --- | --- | --- |
| `PASS` | 建成且可打印 | 交付路径 + 尺寸 + 体积，告知 `.sc` 可在 SolidCraft 里改参数 |
| `UNVERIFIED` | 建成但有可修缺陷 | 跑 `repair` 再 `inspect` 复检，如实报告两次 |
| `FAIL` | 执行失败或结构性不可用 | 读 `reason` 修脚本重跑，**不要**声称完成 |

**失败重试**：`error: step 7 (solid.hole): ...` 里的 `7` 是命令列表第 7 条。
只改那一条，整份重跑——SolidCraft 全有或全无，不需要手动回滚。

## 第 4 步：看懂一个已有设计

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action script --input bracket.sc --output build.json --json
```

把不透明的 `.sc` 还原成 `{"commands": [...]}`，你就可以读它、改它、再用 `--in` 重跑。
`gate.data.notes` 会带上 SolidCraft 的 replay 说明（部分步骤依赖设计格式本身）。

## 第 5 步：量它

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action measure --input bracket.sc --json
```

返回每个 body 的 `volume_mm3`、`area_mm2`、`mass_g`（按设计里的材料密度）、`bbox`、
`closed`、面/边/顶点数与 `face_types`，以及全部参数——回答“多重”“多大”用它，
不要从网格反推。

## 第 6 步：出图

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action snapshot --input bracket.sc \
    --output bracket.png --view iso --width 640 --height 480 --json
```

`--view` 可选 `iso/front/back/top/bottom/left/right`；`--section z=27` 剖切；
`--body NAME:opacity=0.3,color=#rrggbb` 控制单个 body 的显示。产出 PNG，可直接发给用户。

## 第 7 步：外部网格才走 repair

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action inspect --input scan.stl --json
python "${CLAUDE_PLUGIN_ROOT:-.}/run.py" --action repair  --input scan.stl --output scan_fixed.stl --json
```

SolidCraft 的实体导出天然水密，对它跑 repair 基本空转；对它的产物用 `inspect`。

## 硬性约束

- **绝不编造命令名**。拿不准就 `solidcraft-cli commands | grep <关键词>`。
- **绝不因退出码 0 就宣布成功**：`model` 已校验导出文件真实存在且非空，读 gate 的 `status`。
- **绝不修改用户原始 `.sc`**：所有产物写在输出旁边，原件不动。
- **绝不把 `step` 输出当作可打印**：B-rep 无三角网格，要打印需另导 STL。
- 报尺寸时带上 `assumed_units`（STL 无单位，报告按 mm 处理并已注明）。

## 已验证的 CLI 行为（SolidCraft 0.30.1）

- `run <script.json|design.sc|part.step> --out FILE...` 按扩展名导出，`--out` 可重复；
  `--in design.sc` 把脚本叠加在已有设计上；`--save` 存设计；`--results --json-out` 出步骤清单。
- `eval <design.sc|part.step> --json-out FILE` 返回 B-rep 测量。
- `snapshot --in <design> --out PNG [--view] [--width] [--height] [--section] [--body]` 渲染预览图。
- `script <design.sc> --out FILE` 把设计还原成命令脚本。
- 真实失败退出码为 **1**，stderr 形如 `error: step N (cmd): ...`。
- 网格精度是导出命令的参数而非 `run` 的开关，`--quality fine|finest` 会注入
  `file.export_stl`；`.sc` 设计无法注入，使用默认精度并在 `notes` 记录。
