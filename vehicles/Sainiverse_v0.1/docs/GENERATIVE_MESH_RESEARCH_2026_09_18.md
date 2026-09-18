# Sainiverse：生成式 Mesh 工作流调研

检索日期：2026-09-18。范围：Meshy、Hyper3D Rodin、Tripo 官方 API、更新记录及第一方技术说明；对照当前本地项目。本文是文档调研，不是生成模型实测：没有提交付费生成，没有下载这三家输出并做同条件 A/B，也没有依据宣传图评出绝对冠军。

## 判断

**值得引入，局部外观有较大的提升潜力；目前没有证据证明直接替换整个工作流会让整车或驾驶舱全面达到用户要求。** 当前程序几何在座椅、软包、护套、手柄、随车物品等具有设计曲面和材料细节的部件上仍有明显余地。生成式模型可以成为这些资产的另一条生产来源，不能先验地因为它不是参数化 CAD 就排除。以下是适用性推断，须由本项目实测验证。

另一方面，用户指出的悬浮、干涉、装配缝隙、控制映射与升降控制器抖动，分别需要装配、碰撞、运动学或控制求解修复。增加视觉网格细节并不直接改变这些实现。即便生成工具能分件，也不能据此推断其已生成符合本项目需求的关节轴、行程、质量和控制语义。

## 当前可核实版本与能力

| 产品 | 本次官方资料可核实状态 | 对项目有意义的能力 | 必须保留的边界 |
|---|---|---|---|
| Meshy | Meshy 7；另有 Smart Topology T2 路线 | 7 面向细节；T2 原生分件、可指定低面数；可对现有模型重新贴图 | T2 与 standard/Ultra 不是一个开关组合，目标面数也不是严格保证 |
| Rodin | Gen-2.5；2026-08 更新了多视向标签、对称、法线烘焙等参数 | 多图约束、Quad/Raw、尺寸包围盒条件、Bang 分件、贴图生成 | 包围盒和对称条件不等于装配公差保证；纹理增强可能引入伪影 |
| Tripo | H3.1，稳定快照 `v3.1-20260211`；纹理 `v3.5-20260815` | 多视图、分件、PBR、分件重拓扑与烘焙 | 原生分件与若干贴图/低模选项不能在一次生成中组合 |

上述版本是检索时官方文档能够核实的版本，不是凭产品旧印象沿用 Meshy 5、Rodin Gen-1 或 Tripo 2.x。

### Meshy

官方 Image-to-3D API 当前将 `latest` 指向 Meshy 7。standard 可选 Ultra；T2 则是独立的 `smart-topology` 类型，原生生成分开的部件、三角面，目标 100–15,000 面。standard 重网格目标为 100–300,000 面；官方说明实际面数可能偏离。`symmetry_mode` 已废弃且无效，不能再用它许诺对称。PBR 可输出 base color、metallic、roughness、normal。[Image API](https://docs.meshy.ai/en/api/image-to-3d)

更新记录列出 2026-08-12 图像/多图 Meshy 7、08-13 文本 Meshy 7，以及 09 月面向打印的 Auto Split。Auto Split 不是保持原有贴图的游戏机械拆件替代品；09-16 记录了不保留原纹理的限制。部分旧网页与 API 的版本描述不同，本报告优先采用带日期的 API 更新记录。[Changelog](https://docs.meshy.ai/en/api/changelog)

Retexture 接受已有模型，支持 `enable_original_uv` 保留原 UV、PBR 和多视图参考。它为保留目前准确结构、单独改进表面提供了一条可测试路线。Meshy 7 重贴图仍有账号分批开放说明，需以实际账号能力确认。[Retexture API](https://docs.meshy.ai/en/api/retexture)

### Rodin

Gen-2.5 接受 1–5 张图，支持视向标签、对称意图、包围盒尺寸条件；可选三角或四边面，支持高模细节烘焙到法线。默认 Raw medium 为 500,000 面，Quad medium 为 18,000 面。PBR 包括颜色、金属度、法线和粗糙度；另有带烘焙光照的 Shaded/Hybrid。官方明确警告 `hd_texture`、`uhd_texture` 可能引入伪影。`creative` 更自由，`faithful` 更接近参考。以上均为控制能力说明，尚不是针对 Sainiverse 精密部件的质量证明。[Gen-2.5 API](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)

2026-07 默认几何策略从 faithful 改为 creative，08 月增加视向标签、对称及法线烘焙等参数。因此测试应显式固定版本、faithful 策略和面数，避免默认行为变化影响比较。[Changelog](https://docs.hyper3d.ai/en/get-started/changelog)

Bang 可处理 Rodin 资产或上传模型，分割强度可调。上传模型若要求生成材质，需要参考图；无材质模式可省略。它让“生成后拆成部件”成为真实可用的接口能力，但此 API 说明没有给出机械关节或运动约束输出保证。[Bang API](https://docs.hyper3d.ai/en/api-specification/bang)

### Tripo

H3.1 官方稳定快照为 `v3.1-20260211`，支持文本、单图、多图及 PBR；最大面数 2,000,000，具有 Quad 与低模路线。官方速度与质量等级属于厂商描述，本次未据此推断实际导入后的品质和耗时。[H3.1 模型页](https://developers.tripo3d.ai/en/models/v3-1)

Image API 明确：smart_low_poly 更适合简单输入，复杂模型可能失败。generate_parts 要求关闭 texture 和 pbr；与 quad 同用会忽略 quad，与 smart_low_poly 同用则不会产生分件。export_uv 可控制展开。贴图模型可独立锁定 `v3.5-20260815` 并去除参考图烘焙光照。修改导出方向后再进行后处理，可能方向错误但任务仍报告成功；应最后转换方向。[Image API](https://developers.tripo3d.ai/en/docs/generation-image-to-model/standard)

多视图支持 front/left/back/right，至少两张且不能省略正面，要求同一对象与一致光照。这允许使用我们自己制作的多视角设计图，但不应把互相矛盾的概念图当成精确约束。[Multiview API](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/standard)

后处理分割支持默认几何 v1 和 `v2.0-20260430` 语义标注 Beta，可提供参考分割图。重拓扑 v2 支持指定部件和贴图烘焙，三角目标 500–20,000、Quad 500–10,000；这比只输出不可分的高模更接近资产流水线。[Segmentation](https://developers.tripo3d.ai/en/docs/mesh-segment)、[Retopology](https://developers.tripo3d.ai/en/docs/mesh-decimate)

作为补充，Tripo 自己的重拓扑技术说明也承认：薄板、邻近开口、倒角、机械缝可能被软化或连在一起。该说明用于界定风险，不作为 H3.1 的量化评测。[官方技术文章](https://www.tripo3d.ai/blog/auto-retopology-ai)

## 与当前实现的对照

本地 `reports/acceptance_build.log` 记录 23,417 个源部件、342 个渲染网格、1,518,574 三角形。问题不能简单归因于全车面数太少：面数分配、曲面设计、纹理密度、材质响应、灯光和装配都影响近景。

`source/surface.gdshader` 的 `surface_kind==11` 外部材质路径读取 albedo/normal，但粗糙度固定为 0.82；`runtime/atelier_review.gd` 外部终端材质只绑定 diff/norm。**当前这一导入路径没有完整利用外来资产的 PBR 通道。** 因此即便生成素材的官网预览很好，也不能保证原样导入这里呈现同样材料效果。应把材质接入和生成资产质量分别评估。

| 对象/问题 | 生成 Mesh 的预期价值（推断） | 仍需当前工程侧负责 |
|---|---|---|
| 座椅软包、布套、行李、救生装备、小道具 | 高；更复杂的形体、缝线与表面变化 | 尺寸、风格、LOD、碰撞与安放 |
| 驾驶台外壳、手柄外形、设备箱 | 中到高；可试作设计曲面 | 孔位、安装面、活动部件分离、行程 |
| 仪表文字、实时刻度、操纵映射 | 有限；可辅助外观 | 清晰字标、实时数据、交互逻辑 |
| 墙面、地板、舱门 | 重新贴图可能更划算 | 开口、UV密度、主题材质、结构闭合 |
| 升降机、履带、悬挂、吊机装配 | 外壳和附件可获益 | 轴线、受力、碰撞、稳定控制 |

## 建议的公平试验

先取同样三类资产：一把驾驶座椅、一个操纵手柄、一个工业设备箱（带薄板通风口）。比较当前程序资产、可用的成熟资源，以及三家生成结果。每类资产每家生成三个样本，用相同设计参考和人工修整时间，保留失败样本，不只挑最好看的官网图。

在同一 Godot 灯光、镜头距离、主题材质、三角形/显存预算下对比：轮廓和近景、背面完整度、孔洞与薄壁、文字/UV、分件可用性、修整耗时、帧时。活动件还要做真实关节行程检查。材质至少比较“现有风格着色器”和“完整 PBR 接入后的风格化处理”两个路径，避免把未接材质误判成生成器不行。

若座椅与设备箱在这些条件下显著胜出，就扩大这条资产流水线；若修整时间超过成熟素材或重新建模，就只保留适合的类别。当前证据支持做这次小规模试验，尚不支持承诺全面切换后质量会提高多少倍，也不支持三者的固定排名。
