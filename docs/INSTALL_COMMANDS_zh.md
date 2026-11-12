# 安装命令

各宿主的完整命令、`install.py` 的全部参数与可选能力。方法一与方法三较短，留在 README：[3d-fabric](../README_zh.md) · [English](INSTALL_COMMANDS.md)

---

## 前置：SolidCraft

3d-fabric 不含实体核，只驱动本机已安装的 SolidCraft。它开源免费（MIT / Apache-2.0 双许可），需要你自己装：

| 平台 | 下载 |
| --- | --- |
| Windows | [solidcraft-windows-x64.msi](https://github.com/tangency-labs/solidcraft/releases/latest/download/solidcraft-windows-x64.msi) |
| macOS | [solidcraft-macos-universal.dmg](https://github.com/tangency-labs/solidcraft/releases/latest/download/solidcraft-macos-universal.dmg)（Apple silicon 与 Intel 共用） |
| Linux | [solidcraft-linux-x86_64.AppImage](https://github.com/tangency-labs/solidcraft/releases/latest/download/solidcraft-linux-x86_64.AppImage)，或 `sudo snap install solidcraft` |

- 完整下载页（ARM64、32 位、便携 zip、`.deb`、`.rpm`、Flatpak）：<https://solidcraft.io/download>
- Windows 安装包目前没有代码签名，SmartScreen 会拦一次：**更多信息 → 仍要运行**。
- 浏览器版 <https://solidcraft.io> 免安装，但它不提供 `solidcraft-cli`，**本插件用不了**。

装完确认命令行能被找到：

```bash
solidcraft-cli --version
```

能打印出版本号就成了——本插件验证过的是 `solidcraft-cli 0.30.1`，更新的版本同样能用。没有输出说明它不在 `PATH` 上（旧版 Windows 安装器不写 `PATH`），这时任选一种方式告诉插件：

```bash
python run.py --action probe --solidcraft "C:/Program Files/SolidCraft/solidcraft-cli.exe"
```

```bash
set SOLIDCRAFT_CLI=C:\Program Files\SolidCraft\solidcraft-cli.exe
```

macOS / Linux 把 `set` 换成 `export`。也可以用 `SOLIDCRAFT_HOME` 指向整个安装目录。

> **只有四个动作需要 SolidCraft**：`model`、`script`、`measure`、`snapshot`。`inspect` 与 `repair` 不需要它——扫描件、下载件、别家 CAD 出的网格，在一台没装过 SolidCraft 的机器上照样能查能修。

---

### 前置：Blender（想用那一半才装）

三十个 Blender 技能需要两样东西，都来自 Blender 生态，本插件不带：

1. **本机 Blender** —— <https://www.blender.org/download/>（4.x 即可）
2. **一个 Blender MCP 服务**，把 Blender 暴露成 `mcp__blender__*` 或 `mcp__blender_official__*` 工具组

缺任何一样，Blender 技能会直接说缺什么，不会假装渲染过；CAD 那一半完全不受影响，`run.py` 一行都不碰 Blender。

---

## 方法二：用命令安装

**Claude Code** —— 在终端执行，注册市场与安装一步完成：

```bash
claude plugin install 3d-fabric --marketplace https://github.com/JiamingShi-JsPhys/3d-fabric.git
```

**Claude Code** —— 在会话内执行，先按发布 tag 添加市场：

```text
/plugin marketplace add https://github.com/JiamingShi-JsPhys/3d-fabric.git#v1.1.1
```

再安装它列出的条目：

```text
/plugin install 3d-fabric@3d-fabric-marketplace
```

**Codex** —— 把 URL 注册为 Git 市场；`--ref` 锁定发布 tag，HTTPS 换成 SSH 或本地路径同样可用：

```bash
codex plugin marketplace add https://github.com/JiamingShi-JsPhys/3d-fabric.git --ref v1.1.1
```

```bash
codex plugin add 3d-fabric@3d-fabric-marketplace
```

**dsh（DeepSeek Harness）** —— dsh 把插件当 npm 包装，仓库里因此还带 `package.json` 与 `cordis.patch.yml`，由 `index.js` 把技能注册进 dsh 的技能表：

```bash
dsh plugin --profile desktop add github:JiamingShi-JsPhys/3d-fabric#v1.1.1
```

`package.json` 里没有 `dsh.bundle.patch` 的包 dsh 一律拒收——就是「这个包没有声明组合包」（内部原因码 `reasonNotBundle`）。升级要先卸载：dsh 不会原地替换已安装的版本。

**CodeBuddy** —— 与 Claude Code 同一套命令：

```text
/plugin marketplace add https://github.com/JiamingShi-JsPhys/3d-fabric.git#v1.1.1
```

```text
/plugin install 3d-fabric@3d-fabric-marketplace
```

**Cursor、Windsurf、Cline、Continue、Roo Code、GitHub Copilot、opencode** —— 各家从自己的位置读取规则文件，而且都不接受本仓库作为插件：Cline 的插件格式是 JS/TS 包，Cursor 的插件是另一套打包，`opencode plugin <module>` 装的是 npm 模块。**没有任何厂商提供能识别别家规则文件的安装器**，所以本仓库自带一个：

```bash
git clone https://github.com/JiamingShi-JsPhys/3d-fabric.git && python 3d-fabric/install.py --project <项目>
```

这一条命令会一次性写好全部项目级规则文件：

- `.cursor/rules/3d-fabric.mdc`（`alwaysApply`）
- `.windsurf/rules/3d-fabric.md`（`trigger: always_on`）
- `.clinerules/3d-fabric.md`
- `.continue/rules/3d-fabric.md`（`alwaysApply`）
- `.roo/rules/3d-fabric.md`
- `.github/copilot-instructions.md`
- `AGENTS.md` —— Codex、opencode 与 Copilot Agent 都会读的通用契约

`--global` 另外写用户级的两份：`~/.config/opencode/AGENTS.md` 与 `$CODEX_HOME/AGENTS.md`（默认 `~/.codex/`），本机没有的宿主直接跳过。Claude Code 故意不在其中——它有插件渠道，而 `~/.claude/CLAUDE.md` 属于用户自己。

克隆下来的仓库要放在 Agent 能访问到的位置：每个规则文件都点名 `run.py` 与 `scripts/`，宿主因此能像插件宿主一样调用同一个引擎。规则文件只描述"怎么调用"，并不内置代码。

重复运行是安全的：内容相同的文件报 `unchanged`，已经改过的规则文件在你不加 `--force` 时保持原样。每个规则文件都是 `AGENTS.md` 的逐字正文加该宿主自己的头部，改一处就同步到六处——`tests/test_plugin_manifests.py` 会在它们漂移时报错。

**opencode 也可以完全不复制** —— 用 `opencode.json` 的 `instructions` 数组原地指向规则文件：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["../3d-fabric/AGENTS.md"]
}
```

---

## `install.py` 的全部参数

```text
python install.py                      # 等同于 --check
python install.py --check              # 报告 python / 几何栈 / SolidCraft / examples
python install.py --deps               # pip install -r requirements.txt
python install.py --skill-dir [路径]   # 把技能复制到宿主技能目录（默认 ~/.claude/skills/3d-fabric）
python install.py --project <项目>     # 写全部项目级规则文件
python install.py --global             # 写用户级规则文件，跳过本机没有的宿主
python install.py --only cursor,codex  # 只装其中几家
python install.py --list               # 只列目标，不写盘
python install.py --dry-run            # 预演
python install.py --force              # 覆盖已存在的目标
```

`--check` 的四个检查项逐项给结论；任一失败都会告诉你缺什么、怎么补。

---

## 手动：不用任何插件系统

克隆之后原地跑：

```bash
python -m pip install -r requirements.txt
python run.py --action probe
```

或者把技能连同它的依赖一起复制到一个技能目录：

```bash
python install.py --skill-dir ~/.claude/skills/3d-fabric
```

`--skill-dir` 会一起搬 `run.py`、`scripts/` 与 `references/`——但它只装 CAD 那一个技能；三十个 Blender 技能走插件渠道，那里的 `allowed-tools` 才会被尊重。命令在技能里写作 `python "${CLAUDE_PLUGIN_ROOT:-.}/run.py"`，没装成插件时会回退到技能目录本身。

---

## 可选能力与依赖

```bash
pip install -r requirements.txt    # 核心：trimesh、numpy、scipy、networkx、lxml
pip install numpy-stl              # 仅测试用：独立 STL 读取器
```

完整的"能力—依赖—缺失时行为"矩阵见 [DEPENDENCIES.md](DEPENDENCIES.md)。`inspect` 与 `repair` 只需要 trimesh；`model`、`script`、`measure`、`snapshot` 另外需要本机 SolidCraft。
