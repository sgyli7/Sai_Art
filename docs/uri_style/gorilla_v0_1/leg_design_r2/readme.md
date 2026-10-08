# Gorilla R2 腿部造型交接包

先看 `images/uri_leg_concept.png` 和 `images/leg_review.png`，再看 `design_brief.md`。

三段 Z 型、默认屈膝、低脚踝、重做的贯通脚底。常态约 2.26 m，进一步屈膝约 2.00 m；不再追求旧的 2.65 m。

孔位、轴承、材料壁厚、驱动与承载验算由「启动 Gorilla V0.1 工程方案」负责。本包交付可编辑造型提案，用户尚未验收；不代表数吨承载或制造放行。

导入使用 `source/leg_design_legs.glb`（仅新腿，glTF Y-up），或 `source/leg_design_scene.json`（米制 X 前 / Y 左 / Z 上）；关节位置独立列在 `source/joint_layout.json`。`source/leg_design_context.blend` 和下蹲版均可独立打开编辑。

原生视图严格使用同一几何，121 个指定姿态未发现有限造型体穿插或穿地。几何检查未包含新版实际驱动、载荷或结构强度。URI 原画是同源几何指导的画面润色，细缝与表面处理以概念属性使用。

上身设计依据是 `references/approved_upper_aa3.png`。整机预览的 C15 上身只用于空间与比例参照，不能替换已认可原画。

原生文件和查看本包无需原工程仓库。Python 重建脚本则依赖本 Art 工作区的 `leg_redesign_r1/native` 定位源、三角网格工具与 Blender；本包不是工程仿真启动器。

文件版本和证据绑定见 `handoff_manifest.json`。旧 R1 六缸布置在整机合装中存在干涉，不能继承其单腿通过结论或当成本版有效驱动方案。
