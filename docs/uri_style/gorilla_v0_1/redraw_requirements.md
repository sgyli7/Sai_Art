# Gorilla V0.1 完整重画约束

用户要求 GPT 6.1 SOL 继续本任务。已向当前任务提交模型覆盖；内置 imagegen 是独立图像工具，其模型版本未公开。V 稿已被用户否定，不能用于三视图定稿或交付。

1. 严格正面中心轴，双侧对应组件、关节高度、轮廓、色块、足底高度一致；不歪、不扭、不单腿前后错位。
2. 上侧护具与散热口下的侧板恢复原有亮蓝；不擅自加入深蓝。最新四张配色参考决定大色块分配：成片蓝、实质面积黄橙、次级暖白；不是只增加微小黄色标签。
3. 中央顶部和两侧护具各自有体积、纵深与结构分配。用户画的是可读的六面体体块关系，连接处留真实间隙，不是贴合到严丝合缝。连续复杂曲面保留，但不能恢复球盖、平盖、凹顶，也不能靠新增棱脊、凸饰或层叠甲片形成攻击性。整体高度锁定，不因“抬高”解释增加高度。
4. 肩内侧、腰髋、肘部减少无意义铁球、钢柱、帽盖和重复连接件；保留必要主驱动和承力连接。删减几何不等于删减涂装颜色，不能用外加盖板掩盖同一堆无意义件。
5. 三段承力腿形成自然 Z 姿态：髋—大腿—膝 J1—中段—额外折转 J2—短末段—踝 J3—脚。三段腿不能退回普通膝腿，也不能增加装饰第四段。中段与短末段有主次，轮廓连贯，不能两段相同甲片重复。
6. 足部低矮、宽接地、硬朗且少零件；参考原有工业机甲足，不是鞋盒、厚围边、堆叠盖片、叉爪或细轨。两脚同形、同宽、同高，保留单个必需踝连接和完整接地面。
7. 项目 uri-style 固定三原图、规范、精确提示和实际输入来源随生成保存；完成结构/洁净/优雅/风格/主体分别核对，不能只改漆面。
8. 尺寸仍采用冻结 Blender 包络 H2.650 m、W2.586977 m 含臂、D1.071836 m；粗模只给尺寸，不移植其方块外形，不声称绘图是同源工程 CAD 或数值拓扑最优解。
9. 修正稿完成后继续同尺度正／左／后三视图，核对连杆数、关节高度、脚尖脚跟方向、色块与分件对应。随后打包到 Sai_Rotbots 并进行用户已授权的 handoff。现阶段尚未交付。

已保存 V2 提示草稿，但尚未调用；执行前按上列完整约束再查，不能当作全部反馈天然已落实。

已生成数值视图合同与矢量姿态示意，仅为新布局提议，未进入生成输入。SVG 转 PNG 时 cairoSVG 不可用，未安装依赖、未做新模型；不要误记 PNG 或三视图已经生成。

## Latest correction: original depth authority

User explicitly keeps X width and Y height of W; rejects Z-depth. Original reference owns wedge/tetrahedral core depth and structural mass. Invented near-square projected ratio and sagittal joint anchors withdrawn. Necessary compound foot retained; only redundant parts removed. W2 prompt not called.

## Latest annotation clarification

1. Whole upper core is a wedge/tetrahedral volume with intrinsic continuous curvature, not planar tessellation.
2. User authorizes discarding and rebuilding legs rather than patching old errors. Approved projected X-width/Y-height remains; new side skeleton and compound foot must correspond in all views.

## Latest seven local annotations

Radiator faces point directly forward in all views; LEFT only sees side/edge. Simplify inner shoulder and hip entities at five marked locations. Entire FRONT central pelvis lid orange, corresponding visible front edge in LEFT. Retain new Y3 compound feet and all other regions.


## Latest authoritative region lock (supersedes broader repaint/rebuild instructions)

User selects FRONT and REAR from `images/original_wedge_rebuild_rev_z1.png` / original `exec-bbaf647f-d43d-465a-a286-a8ecfac077ab.png` unchanged. Entire paint allocation uses that reference. Do not redraw/recolor these two views or infer approval of its old LEFT geometry. Only rebuild LEFT and TOP to match their components, same-scale part heights and paint, keeping original curved tetrahedral torso reference. Standard layout FRONT upper-left, LEFT upper-right, REAR lower-left, TOP lower-right.

Six explicit remaining corrections: TOP sees only a sliver of the front vertical lamp; radiator front planes are edge-on from TOP, no upward-facing nostrils; yellow accents have same actual component location across views, no invented opposite accents; LEFT body side must retain the blue side fields visible in locked FRONT/REAR; upper core is a wedge/tetrahedron with intrinsic curvature, not an egg. No new large nose or inflated front projection.

The saved Z8 whole-sheet repaint prompt is cancelled before execution by this new FRONT/REAR lock. No G44 execution for that prompt. No handoff; still user review.

## User-authorized exceptions to selected FRONT/REAR lock

Only three local changes are allowed on selected G37 FRONT/REAR: both radiator grille planes straight forward; reduce unnecessary inner hip entities at FRONT (23.9%,39.3%) and matching side; reduce unnecessary inner shoulder entities at REAR (71.3%,20.7%) and matching side. All remaining silhouettes, proportions, armor boundaries, legs/feet and palette stay fixed. Apply these limited corrections before deriving LEFT/TOP.
