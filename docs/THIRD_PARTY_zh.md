# 随附第三方材料

`references/solidcraft/` 收录了 SolidCraft 为它自己的 MCP 服务发布的四份 Agent 参考文档——**modeling**、**editing**、**checking**、**mechanisms**——连同 `solidcraft-checking` 一起分发的小工具脚本和设计模板。本插件的技能靠它们查命令形状、平面轴、id、回复大小，以及那些"建出来但几何是错的"陷阱。

[English](THIRD_PARTY.md) · **简体中文**

## 准确地说

- **逐字，唯一例外是上游自己的测试。** 每个文件都与上游 `github.com/tangency-labs/solidcraft` 的 `main` 分支字节一致（2026-11-06 取回）；没有改写或合并。唯一没有复制的是 `scripts/tests/`——829 行上游辅助脚本的测试，本插件从不运行它。
- **是参考资料，不是技能。** 文件头里的 YAML frontmatter 是上游原文的一部分；这个目录里没有任何东西注册为 Claude Code 技能，`run.py` 也不会执行其中任何一行。
- **MIT，声明完整。** SolidCraft 是 MIT OR Apache-2.0 双许可，这里按 **MIT** 收取。版权归 SolidCraft contributors（2026）。[`LICENSE-MIT`](../references/solidcraft/LICENSE-MIT) 是完整 MIT 文本，[`NOTICE`](../references/solidcraft/NOTICE) 是上游的署名文件。这些文件仍属贡献者版权，不在 3d-fabric 自己的 MIT 授权范围内；`references/solidcraft/` 之外的部分是 Jiaming Shi 的 MIT 作品。
- **可选。** 删掉这个目录，`run.py` 照常工作——只是失去内置命令参考，回退到 `solidcraft-cli commands`。

## MCP 名字不是 CLI 名字

上游文本按 SolidCraft 的 MCP 工具名书写（`batch`、`execute`、`measure`）。`{"commands": [...]}` 里的命令名与之一致，但 MCP 的调用名 `solidcraft-cli run` 不认。两者冲突时以 `solidcraft-cli commands` 为准。

## 来源

逐文件 SHA-256、取回日期与更新步骤见 [`references/solidcraft/README.md`](../references/solidcraft/README.md)。`tests/test_references.py` 在文件与哈希不一致时报错，所以这张表不会悄悄漂移。
