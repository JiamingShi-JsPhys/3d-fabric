# 3d-fabric 参考

快速上手放不下的内容都在这：七个动作与它们的参数、gate 记录、退出码、依赖对照、仓库布局与测试套件。

[English](REFERENCE.md) · **简体中文**

## 七个动作

| 动作 | 作用 | 需要 SolidCraft |
| --- | --- | --- |
| `probe` | 定位并验活 CLI | ——（就是找它） |
| `model` | 跑脚本、导出、自动体检；`--in` 修改已有设计 | **是** |
| `script` | 把 `.sc` / `.step` 还原成 `{"commands": [...]}` 脚本 | **是** |
| `measure` | 从 B-rep 读体积、质量、面积、包围盒、面类型与参数 | **是** |
| `snapshot` | 渲染 PNG 预览（视角、剖切、按 body 设色） | **是** |
| `inspect` | 任意网格的打印前报告 | 否 |
| `repair` | 焊点、补洞、修法线 | 否 |

所有动作都接受同一组全局参数：

| 参数 | 含义 |
| --- | --- |
| `--action` | 上面七个之一（必填） |
| `--input` | 请求 `.json`、`.sc` / `.step` 设计，或网格文件 |
| `--output` | 结果写到哪里（`model` 可按 `--format` 重复给多个） |
| `--solidcraft` | 显式指定 `solidcraft-cli` 路径 |
| `--root` | 工作区根目录；gate 写到 `<root>/process/gates/` 下 |
| `--report` | 把 gate JSON 写到这个确切路径 |
| `--json` | 在 stdout 打印一行 JSON 形式的 gate |
| `--timeout` | 调用 CLI 的超时秒数（默认 300） |

各动作自己的参数：

| 参数 | 动作 | 含义 |
| --- | --- | --- |
| `--in`、`--design` | `model` | 在已有设计上叠加脚本，原文件不动 |
| `--script` | `model` | 与 `--in` 搭配使用的 `{"commands": [...]}` 文件 |
| `--format` | `model` | `stl`（默认）、`step`、`3mf`、`obj`；可重复 |
| `--quality` | `model` | `standard`、`fine`、`finest`——作为导出命令的参数注入脚本 |
| `--prompt` | `model` | 自然语言需求，记进报告 |
| `--script-out` | `model` | 把落地后的脚本写到哪里 |
| `--save-design` / `--no-save-design` | `model` | 保留或跳过导出文件旁边那份可编辑 `.sc` |
| `--keep-results` | `model` | 保留逐步结果旁车文件；路径在 `data.results_path` |
| `--scale`、`--scale-xyz`、`--translate`、`--rotate`、`--center` | 任意 | 建模之后、出报告之前作用于网格 |
| `--no-fill-holes`、`--max-hole-loop`、`--planarity-tol`、`--ascii` | `repair` | 跳过补洞、扇面补洞的顶点上限、共面性保护、ASCII STL |
| `--view`、`--width`、`--height`、`--section`、`--body` | `snapshot` | 视角名、图像尺寸、剖切、按 body 设色（`NAME:opacity=0.3,color=#rrggbb`，可重复） |

## Gate 记录

每个动作都以一份记录收尾，由 `--json` 打印，并写入 `--report`；给了 `--root` 时写入
`<root>/process/gates/3d-fabric_<UTC 时间戳>.json`：

```json
{
  "skill": "3d-fabric",
  "status": "PASS",
  "evidence_level": "EMPIRICAL",
  "reason": "watertight, winding consistent, manifold",
  "artifacts": ["bracket.stl", "bracket.sc", "bracket.solidcraft.json"],
  "timestamp": "2026-11-12T10:21:33.412Z",
  "data": {
    "action": "inspect",
    "verdict": "ready_to_print",
    "printability": {
      "verdict": "ready_to_print",
      "repairable": true,
      "issues": []
    }
  }
}
```

`status` 只有 `PASS`、`FAIL`、`UNVERIFIED` 三种。`data` 装各动作自己的载荷：`inspect` 的分析结果、
`repair` 的前后拓扑、`measure` 的总量与逐 body 读数、`snapshot` 的图片路径与尺寸、`script` 还原出的
命令列表，以及任何跑过 `solidcraft-cli` 的动作的步骤清单、退出码与 stderr。

gate 文件名带毫秒，同一秒内结束的两次运行会写成两个文件。

## 退出码

| 码 | 含义 |
| --- | --- |
| 0 | `PASS`——动作成功且 gate 通过 |
| 1 | `FAIL`——动作无法完成，或网格被判 `blocked` |
| 2 | `UNVERIFIED`——动作跑了但给不出判定（`needs_repair`、缺 SolidCraft、输入读不出来） |

用法错误（未知动作、缺 `--input`）同样退出 2，因为 argparse 就是这么做的；stderr 上的信息用来区分
它和 gate 判定。

## 依赖

`docs/DEPENDENCIES.md` 是「能力 × 包 × 许可 × 必装或可选」的对照表，也写明某个包缺失时各动作报什么。
简言之：`trimesh`、`numpy`、`scipy`、`networkx`、`lxml` 必装；`opencv-python`、`Pillow`、`scikit-image` 是可选项，只有 12 个图像类技能 import；
`numpy-stl` 只用于测试；
SolidCraft 是 `model`、`script`、`measure`、`snapshot` 的前提；Blender 与 Blender MCP 是 30 个随附技能的前提，`run.py` 一行都不需要。

## 仓库布局

```text
3d-fabric/
├── .claude-plugin/                   # Claude Code 插件清单 + 市场
├── .clinerules/                      # Cline 规则文件
├── .codebuddy-plugin/                # CodeBuddy 插件清单 + 市场
├── .codex-plugin/                    # Codex 插件清单 + 市场（含 interface）
├── .continue/rules/                  # Continue 规则文件
├── .cursor/rules/                    # Cursor 规则文件（.mdc）
├── .dsh-plugin/                      # dsh 目录式入口（转调 index.js）
├── .github/
│   ├── copilot-instructions.md       # GitHub Copilot 规则文件
│   └── workflows/ci.yml              # Linux 与 Windows 上跑 pytest，外加一次 CLI 冒烟
├── .gitattributes                    # 统一 LF；二进制网格标记
├── .gitignore
├── .roo/rules/                       # Roo Code 规则文件
├── .windsurf/rules/                  # Windsurf 规则文件
├── AGENTS.md                         # Agent 操作规则——六份规则文件的正文
├── CHANGELOG.md                      # 发布说明
├── LICENSE                           # MIT
├── README.md                         # English quick start
├── README_zh.md                      # 本仓库中文说明
├── THIRD_PARTY_LICENSES.txt          # 上游许可清单 + 与 SolidCraft 的关系
├── cordis.patch.yml                  # dsh：把插件插入 profile
├── docs/
│   ├── ACKNOWLEDGEMENTS.md           # 谁报了什么，改了什么
│   ├── ACKNOWLEDGEMENTS_zh.md        # 同上，中文
│   ├── BLENDER_SKILLS.md             # 30 个随附技能，逐个说明
│   ├── BLENDER_SKILLS_zh.md          # 同上，中文
│   ├── DEPENDENCIES.md               # 能力—依赖—缺失时行为的矩阵
│   ├── INSTALL_COMMANDS.md           # 各宿主完整安装命令、install.py 全部参数
│   ├── INSTALL_COMMANDS_zh.md        # 同上，中文
│   ├── REFERENCE.md                  # English reference
│   ├── REFERENCE_zh.md               # 本文件
│   ├── THIRD_PARTY.md                # 随附 SolidCraft 参考与许可
│   └── THIRD_PARTY_zh.md             # 同上，中文
├── examples/
│   ├── bracket_request.json          # 自然语言 + 21 条 SolidCraft 命令
│   ├── damaged_part.stl              # 带孔的球体，用于 inspect / repair 演示
│   └── make_demo.py                  # 重新生成 damaged_part.stl
├── index.js                          # dsh 入口：把每个 skills/*/SKILL.md 注册进技能表
├── install.py                        # --check / --deps / --skill-dir / --project / --global
├── licenses/
│   └── cc-blender-skill-LICENSE.txt  # 随附技能的上游 MIT 文本
├── manifest.json                     # 技能管线元数据（stage、动作、依赖）
├── package.json                      # 包清单；`files` 决定发布时带哪些
├── pyproject.toml                    # 包元数据 + pytest/pyright 配置
├── requirements.txt
├── references/
│   └── solidcraft/                   # SolidCraft 四份 Agent 参考，逐字收录（MIT）
│                                     #   README.md：来源、哈希、更新步骤
├── run.py                            # CLI：probe / model / script / measure /
│                                     #      snapshot / inspect / repair
├── scripts/
│   ├── engine.py                     # trimesh 几何：加载、变换、分析、修复、导出
│   └── solidcraft.py                 # CLI 桥：探测、执行、eval、snapshot、script
├── skills/
│   ├── vendored.json                 # 上游地址、取回日期、逐文件 SHA-256
│   ├── 3d-fabric/                    # 本插件自己的技能：CAD 一半 + 路由
│   └── <30 个 Blender 技能>/          # 逐字来自 github.com/RobLe3/cc-blender-skill
│                                     #   （MIT）：11 个制作 + 2 个 HUD/动画 QA
│                                     #   + 17 个按参考图重建
└── tests/                            # 仅供开发——不在 package.json 的 files 里
    ├── conftest.py                   # 运行时生成的夹具（仓库里不放二进制）
    ├── stub_solidcraft.py            # CLI 测试桩件
    ├── test_actions.py               # measure / snapshot / script、model --in
    ├── test_bundled_skills.py        # Blender 技能齐全、绑定 MCP、哈希一致
    ├── test_cli.py                   # 退出码、gate 文件、stdout 契约
    ├── test_dsh_bundle.py            # dsh.bundle.patch、CJS 入口、版本一致
    ├── test_engine.py                # 几何、缺陷、修复、导出
    ├── test_install.py               # --check、--skill-dir、参数处理
    ├── test_model.py                 # 完整建模 → 体检链路
    ├── test_plugin_manifests.py      # 四份插件清单 + 六份规则文件不许漂移
    ├── test_references.py            # SolidCraft 参考齐全、哈希一致
    └── test_solidcraft.py            # 探测、执行、失败与"静默不写文件"
```

## 测试

```bash
python -m pytest
```

141 个用例。覆盖几何引擎（STL 加载时的顶点焊接、绕支点的变换、绕序、反向壳体、空腔与反向零件的
区分、每一类缺陷、四边形与 32 边形边界的补洞、用独立 STL 读取器验证的导出往返）、CLI 契约（退出码、
gate 文件、人类可读与 `--json` 两种输出）、读设计的动作（`measure` 的总量与开口体、`snapshot` 的 PNG
产物、`script` 的还原、`model --in`）、随附参考（文件齐全、按 README 表校验 SHA-256、MIT 文本、
`install.py --skill-dir` 会一并复制）、随附 Blender 技能（齐全、frontmatter 名字与目录一致、每个都
绑定 Blender MCP 工具、跨技能相对链接可解析、哈希与 `skills/vendored.json` 一致）、dsh 包
（`dsh.bundle.patch` 声明、CJS 入口能列出全部 31 个技能、与 Claude Code 清单的版本一致）、平台那一层
（四份插件清单与六份规则文件，每份规则文件都锁定到 `AGENTS.md`）、安装器自身的检查，以及通过 Python
桩件驱动的 SolidCraft 桥——所以无论本机装没装 SolidCraft，测试都通过。装了真机时会额外跑一条集成用例，
没装则跳过。

测试套件属于仓库，但不属于发布包：`package.json` 用 `files` 列出发布内容，`tests/` 不在其中。
