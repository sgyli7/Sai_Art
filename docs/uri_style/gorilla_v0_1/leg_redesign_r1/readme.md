# Gorilla R1 历史定位与结构探针

本目录现保留历史定位源与试验记录。**最新造型交接入口是 [R2 腿部造型包](../leg_design_r2/readme.md)**，不是这里的六缸装配。用户已明确：本任务负责造型；孔位、轴承、材料壁厚、驱动与承载验算由「启动 Gorilla V0.1 工程方案」负责。

R1 六缸模型的单腿检查不能代表整机通过。后续 [整机有限几何检查](native/whole_fit_report.json) 查出其驱动／叉座与手掌等部件干涉；该装配未被采用。紧凑驱动筛选也未得到有效完整组合。以下已通过记录仅保留原来的单腿范围，不能作为当前交付结论。

当前方向：按用户给定的两张机甲参考重建整条腿到脚底的支撑链。用户明确允许降低整机高度，原 2.65 m 高度目标已解除，不能为维持旧高度拉长腿。上身造型与 URI 配色仍按原批准版本。此前“保留原有脚掌”的解释已撤回，脚架和接地垫属于本次重建。

历史单腿制作源是 [native/assembled_scene.json](native/assembled_scene.json)，对应 [Blender 装配](native/assembled_candidate.blend)、[屈膝端点装配](native/assembled_deep_crouch.blend) 和 [制作脚本](native/build_candidate.py)。这些是有限材料结构检查模型，**不是最终外观图或制造交付**。该探针的视图来自模型，未调用生图工具；R2 原画另有生图记录。

三段轴距为 **0.68／0.68／0.50 m**，总长比上版 0.83／0.83／0.63 m 缩短约 19%。基准绝对倾角从向下竖直线计为 **前 45°／后 70°／前 40°**，深屈膝端点为前 55°／后 80°／前 50°。基准髋高由 1.66 m 降至 **1.274 m**，端点髋高 **1.008 m**。整体总高须在保留上身的实际合装后确定；这些参数是本轮候选尺寸，不能称为参考图片的精确测量。

小腿承力颊板连续延伸至低位踝轴座，脚架嵌在颊板之间，前后接地垫由共同载体支撑。三段分别连接，额外折点处于腿的中段。六个有实体缸体／活塞杆的定制液压缸候选通过安装叉座与销轴连接。关节、主体、缸径、壁厚及足架没有随腿长等比缩小。

## 已运行的检查

- [121 姿态装配检查](native/assembly_grounded_path_report.json)：全部不同刚体材料对均进行有限实体 CSG 检查，无零件相交、非接地件穿地或驱动超行程；每个刚体的钢结构材料连通。有限采样路径不是独立关节限位范围或连续运动证明。
- [单腿加载仿真](native/loaded_leg_probe_report.json) 和 [MJCF](native/loaded_leg_probe.xml)：自由根节点，实际双驱动的六条滑动关节力路径和六个端点闭环，只有脚垫与地面接触。没有焊到世界、没有主关节理想转矩电机，也没有根节点支撑力。基准保持 2 s、深屈膝保持 2 s、屈膝运动 4 s，共 40000 步，最大关节跟踪误差约 0.066°，无求解器警告。
- [动态实体回查](native/loaded_material_replay_report.json)：80 个动态状态，所有不同刚体材料对回查，无零件相交或非脚垫穿地。脚垫数值接触穿入约 0.13 mm，接触参数未按真实材料标定，不能将它当作弹性垫实测压缩量。

加载模型含 **6000 kg 虚拟试验配重**（2200 kg 临时上身预算、800 kg 另一腿预算及 3000 kg 等效下压力），配合 1.5 倍重力作筛查。这些是明确的试验假设，不是实际整机质量或有效载荷认证。当前单腿有限钢结构、缸体和脚垫的密度积分质量约 **593 kg**，仍不含油液、阀、管路及其他真实器件。驱动采用 30 MPa、效率 0.85 的参数化定制提案，并非已选 OEM 产品。

整机合装碰撞已经查出失败；仍未证明完整整机平衡、髋部实际连接、滚转及三维地形动作、制造配合／紧固／拆装、实际压力器件、材料等级、应力／疲劳／热能力。所有报告保持 `physical_accepted=false`。刚体单腿仿真稳定不能替代上述检查，也不能据此声称能承载数吨。

MuJoCo 闭环连接方式参照 [官方 MJCF connect 文档](https://mujoco.readthedocs.io/en/stable/XMLreference.html#equality-connect)。所有质量、惯量和视图由同一有限几何源派生；外观固定图与 Sai_Rotbots 活动工程源没有覆盖。

## 版本与历史

[方向记录](native/decision.json) 保存最新用户约束、参考图片哈希和高度约束的解除。[tall_stance_superseded_20261003](native/history/tall_stance_superseded_20261003) 保存不再采用的长腿版；[shorter_extra_30deg_rejected](native/history/shorter_extra_30deg_rejected) 保存缩短后继续叠加旧 30° 额外折叠造成相交的拒绝版。旧图生稿及旧布局计算是历史失败或早期筛查，不是当前源。

复跑顺序：`build_candidate.py` → `check_grounded_crouch.py` → `screen_drives.py` → `select_drive_set.py` → `select_finite_assembly.py` → `assemble_drives.py` → `check_candidate.py assembled_scene.json --grounded` → `run_loaded_leg_probe.py` → `check_loaded_material_replay.py`。最后使用 Blender 执行 `render_candidate.py -- assembled_scene.json`。选取无解时必须停在该阶段，不能复用过期选择。
