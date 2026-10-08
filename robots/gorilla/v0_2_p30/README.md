# Gorilla V0.2 外观交付 · P30

本轮外观稿已按用户结束设计迭代的指示冻结。五款配色为 URI、黄紫、白橙、黑金、沙漠，完整 FRONT / LEFT / REAR / TOP 均在 `themes/images`。打开 [五款预览](themes/index.html) 或 [正面总览](themes/theme_overview.png)。

新版沿用 Gorilla 身体身份与屈曲站姿，更新腿部、完整踝足、暖白主护膝与蓝色侧盖、下缘深色机械嵌件、胸前感知舱及黄色框、踝部黄色点缀。前双口为散热进气，后背 pad 两侧为出气；顶壳为一体无缝曲面。其余四款按同一模块角色映射既定色板。

## 3D 资产

- `model/source/lower_modular_components_b7.blend`：用户指定的 B7 灰色腿部资产原文件，未因本轮配色改动。
- `model/exports/lower_modular_components_b7.glb`：同一 B7 的自包含交换副本，38 个共享几何定义、76 个左右腿部件实例、85 个层级节点。
- `model/previews/lower_modular_components_rear_oblique_b7.png`：与用户指定图对应的原始模型预览。另附四个原生视角、前斜视与两张踝部细节。
- `model/reports`：原始几何报告、导出来源和交付前 GLB 检查。

Blender 源采用外观归一化单位，+X 横向、−Y 前向、+Z 向上；GLB 由 Blender 原生导出为 +Y 向上。没有新增整机米制总高或制造尺寸。工程接入应先映射实际尺度与接口。

左右腿使用共享主网格镜像。本包保留原 B7；原报告的闭合实体资格仍为 false，三块高密度拟合罩壳的拓扑缺陷保留在报告中。绘图的法线/透视修订、配色和实际制造实体资格分别记录；本轮没有将图稿变更伪称为同版整机 CAD，也没有重做承载、运动或碰撞门禁。可编辑 3D 交付范围是选定的腿部 B7，整机四视图属于外观稿。

## 来源与维护

制作源：Sai_Art `docs/uri_style/gorilla_v0_2`。色板沿用 V0.1 的五主题定义，几何/构图以当前 P30 定稿为准。旧 AA3 的腿和 TOP 仅出现在历史色板参考中，不作为当前外观结构。`provenance` 保存准确提示词和参考角色，`manifest.json` 保存包内 SHA256 与源路径。

四视图 SVG 嵌入原始 PNG 字节，总览 SVG 引用包内相同图片，均为排版资源；Blender 文件为可编辑 3D 制作源。包内不包含被拒绝的 P22 整机拼装、C15 上半身猜测或 P25 着色实验。P31 的进一步视角草案在用户结束设计后未生成。
