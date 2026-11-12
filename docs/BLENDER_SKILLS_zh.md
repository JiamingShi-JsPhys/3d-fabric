# Blender 那一半——随附的 30 个技能

`skills/` 里随附 30 个技能，逐字来自 [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill) 的 commit `a2634b5`（MIT）。每个技能都在 `allowed-tools` 里声明了自己的 Blender MCP 工具，所以只有在接了 Blender MCP 的会话里才会激活。

[English](BLENDER_SKILLS.md) · **简体中文**

**这一半需要什么：** 本机装有 Blender，并接上一个 Blender MCP 服务（ahujasid/blender-mcp 的 `mcp__blender__*`，或 `mcp__blender_official__*`）。没有它们，CAD 一半照常工作；这些技能会直接说缺什么，不会假装渲染过。

## 制作（11 个技能）

| 技能 | 负责 |
| --- | --- |
| `text-to-blender` | 路由：判断该用哪个子技能、MCP 后端说明、装配顺序 |
| `blender-modeling` | 网格、基本体、修改器、bmesh、硬表面 |
| `blender-materials` | Principled BSDF、金属度开关、清漆/织物/次表面/透射、程序化纹理 |
| `blender-lighting` | 三点布光、HDRI、色温、灯光分组 |
| `blender-cameras` | 焦距、景深、构图、动画相机 |
| `blender-rendering` | Cycles 与 EEVEE、采样、降噪、AgX/Filmic、输出格式 |
| `blender-animation` | 关键帧、F 曲线、缓动、形态键、驱动器、NLA |
| `blender-export` | glTF/GLB、FBX、OBJ、USD、STL、碰撞体、法线烘焙 |
| `blender-uv-texturing` | 展开、图集、投影、烘焙、贴花 |
| `blender-pro-workflow` | 场景装配顺序、评审协议、时间预算 |
| `blender-skill-harmonizer` | 多个技能同时适用时的优先级与交接 |

## HUD 与动画质量门（2 个技能）

| 技能 | 负责 |
| --- | --- |
| `orbital-hud-motion` | 环绕主体的 HUD 圆环、光晕、轨道弧 |
| `animation-quality-gate` | 接触表、闪烁与剪影检查，决定一段动画收不收 |

## 按参考图重建（17 个技能）

"必须和这张图一模一样"靠的就是这一族：

| 技能 | 负责 |
| --- | --- |
| `reference-to-3d` | 从参考图、正交视图、品牌/吉祥物素材重建 |
| `wireframe-to-3d` | 正交线框图 → 模型，导出 glTF/GLB |
| `mascot-logo-reconstruction` | 带失败门、锁定源文件的吉祥物/标志/头像重建 |
| `orthographic-registration` | 把前/侧/后/顶视图注册进同一套坐标约定 |
| `multiview-constraint-solver` | 判断一个刚体能否满足全部视图，先出约束（不需要 Blender 工具） |
| `multiview-fit-loop` | 对照模板"比较—调整—重复"的闭环拟合 |
| `fit-repair-optimizer` | 把拟合报告变成修复队列 |
| `landmark-fit-repair` | 按命名地标（尖角、边缘、眼睛、轮缘厚度）修形 |
| `reference-analysis-validator` | 在宣称 1:1 之前校验参考素材 |
| `reference-look-calibration` | 对着原图校准材质、灯光、裁切、发光与 HUD 风格 |
| `source-part-segmentation` | 规划参考图如何拆成零件（不需要 Blender 工具） |
| `contour-to-mesh` | 用提取出的轮廓与蒙版直接生成曲面 |
| `atlas-uv-fitting` | 把每个源零件映射到自己的图集矩形 |
| `closed-surface-uv-coverage` | 保证封闭/挤出件的端面与侧壁都被贴图覆盖 |
| `texture-driven-mesh-fitting` | 按贴图或贴花轮廓重塑几何 |
| `texture-state-animation` | 贴图状态切换，不要整图淡入淡出或跳变 |
| `quality-refinement-autoloop` | 结果不达标时自我精修 |

## 这里不改它们

它们是上游文本；路由和本地建议写在 `skills/3d-fabric/SKILL.md` 与 `AGENTS.md` 里。`skills/vendored.json` 记录上游取回日期和每个文件的 SHA-256，`tests/test_bundled_skills.py` 在文件与哈希不一致时报错。

Blender 出的网格要和别的网格走同一条路进打印机：先导出 STL，再走 `run.py --action inspect` 与 `repair`。
