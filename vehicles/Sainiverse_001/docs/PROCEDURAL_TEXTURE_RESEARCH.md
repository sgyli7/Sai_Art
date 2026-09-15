# Sainiverse 001：可批量生成的工业手绘贴图

研究日期：2026-09-16。范围：用成熟的程序化蒙版方法提高贴图密度和变化，保留清晰墨线、平涂与有位置依据的岁月痕迹。本文是研究与实施建议，不代表已安装 Substance、已完成整车烘焙或已通过性能验收。

## 调研结论

**采用“固定结构模板 + 有约束的磨损蒙版 + 可重复种子 + 离线合成”。** 程序化足以批量生成边缘掉漆、印字腐蚀、警戒条和接缝积灰；程序不能替代舱门位置、设备分工和结构连接的设计。

Adobe 的风格化教程直接说明：程序纹理先去除高频细点，再通过模糊和阈值重整为可读色块；实例化材质允许色差与污迹变化；标志图层可复用字形再增加腐蚀。该案例也提醒谨慎使用 Normal/Height。它提供的是风格化工作流依据，不是对用户 Sirin 参考制作过程的证明。[Adobe：Japanese animation style with Substance Painter](https://www.adobe.com/learn/substance-3d-painter/web/japanese-animation-style-with-painter)

Substance 的 Metal Edge Wear 接收曲率、AO、世界法线、位置及附加蒙版，主要让凸边磨损，并允许 AO 暗处抑制效果。因此成熟做法并非把噪声均匀铺满整个模型。[Adobe：Metal Edge Wear](https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-graphs/nodes-reference-for-substance-graphs/node-library/mesh-based-generators/mask-generators/metal-edge-wear)

Adobe 的边损教程使用距离场、膨胀/收缩、方向扭曲、阈值与区域排除蒙版控制破损的范围及形状。可在本项目用二维图像算法实现同类基本运算；这不等于复制其专有节点实现。[Adobe：Create edge damage](https://www.adobe.com/learn/substance-3d-designer/web/create-edge-damage)

## 本轮采用的简化方法

以下是针对本车的设计决定，而非来源原文或工程认证。

| 图层 | 空间依据 | 生成规则 |
| --- | --- | --- |
| 面板线稿 | 已确定的面板分区 | 一套连续外轮廓、固定合页/锁扣位置，细线轻微偏差；不随机叠套方框 |
| 边缘掉漆 | 面板边距、门把周围、下沿碰擦带 | 低频连片蒙版限制在指定边缘；少量不等长缺口；大面留白 |
| 积灰/流痕 | 接缝、通风出口下方、局部排水方向 | 数量有限、方向一致的宽窄污迹；遮蔽区与磨损区分开 |
| Sainiverse 字标 | 同一字体和同一排版母版 | 仅腐蚀掩码种子和程度变化，保留可读性；不重新生成字体 |
| 黑黄警戒条 | 升降台外缘、吊装夹挤边界等明确位置 | 固定斜率和条宽，少量缺漆；不随机贴满墙体 |
| Normal | 实际凹槽、压筋、浅埋锁扣等高度模板 | 从独立高度场求梯度；污渍、字标与大部分掉色只进入颜色/粗糙度 |

建议生成器参数：部件类别、实际宽高、边缘允许区、禁止区、磨损等级、标志种类、种子。种子由稳定部件标识派生，重跑结果一致；同一类别有少量模板、多种磨损变体。各层单独输出，最终合成图集。改变主题只改变主漆色，不把黄吊机、钢铁甲板、字标颜色一并染色。

**本轮二维边距、门缝与接触区是人工定义的语义蒙版，不是从整车模型烘焙得到的曲率或 AO。** 可称“受结构位置约束的程序贴图”，不可称“真实曲率磨损烘焙”。未来曲面或复杂节点需要更精确磨损时，再对 UV 展开的部件烘焙网格信息。

## 后续真实烘焙路径

Blender Cycles 支持将颜色、法线和 AO 烘焙到图像；需要 UV 及活动目标图像节点。切线空间法线适合随物体变换的材质。UV 岛边缘要留扩展像素，避免过滤与 mipmap 产生接缝。以后可从整车原生模型输出这些网格信息，再替换上述二维近似输入。[Blender 官方 Render Baking 文档](https://docs.blender.org/manual/id/4.4/render/cycles/baking.html)

不要直接从彩色磨损照片求法线：色差不等于高度。当前独立高度模板仅模拟浅表结构，也不能修正错误几何、穿模或接合关系。

## Godot 成本与验收

Godot 官方建议 3D 纹理使用 mipmap，减少远处颗粒和带宽；代价约为多 33% 显存。RGBA8 的 2048² 纹理连 mipmap，官方估算未压缩约 21.33 MiB、VRAM 压缩约 5.33 MiB。PNG 文件变小不等于显存减少。法线使用 OpenGL 的 X+/Y+/Z+ 约定；自定义 shader 若启用 RGTC 法线压缩，不能继续假设蓝通道原样保留。[Godot：Importing images](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html)

项目执行建议：离线生成，运行时复用少量图集与材质；图集格子保留边界扩展和足够留白，并用 mipmap 近远景检查串色；先用有限分辨率验证字标可读性，不盲目给每个部件一张独立 4K。图集本身不会自动合并所有绘制调用，仍需检查现有材质分组和实际性能。

验收必须包含：同一近景修复错位面板；同字体不同腐蚀的并排对比；警戒条只出现在指定区域；污迹不变成密集点状凹凸；四主题图层一致；远景无闪烁/串色；记录面数、共享纹理数和实际 Godot 帧时间。研究阶段未执行这些验收。
