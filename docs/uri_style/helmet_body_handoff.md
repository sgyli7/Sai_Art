> 历史U方案：用户已明确否定巨面具和膨大肩壳。其头身组织不能作为当前底图或验收标准。最新候选与设计解释见[integrated_core_handoff.md](integrated_core_handoff.md)。工程经验段落仍可查阅，但不证明任何新图的制造能力。

# 低位头体 × URI工业机甲：交给Sai_Robots的设计说明

2026-10-01。**当前为概念候选，不是制造发布或载荷验证。** 外观为[helmet_body_concept.png](helmet_body_concept.png)，造型理解见[wataru_design_grammar.md](wataru_design_grammar.md)，完整实际提示见[helmet_body_prompt.txt](helmet_body_prompt.txt)。

## 设计的组织关系

肩背在后上方，中央头面位于前下方，短腹甲连接紧凑骨盆；头体占据一部分传统胸腹空间，面部仍保持完整辨识。它不是独立头塞进胸口凹槽，也不是一颗球形头取代全部上身。上身围绕这套前后叠置重新生成，N至T的失败上体没有作本次底图。

战神丸用户图与幻神丸官方图只提供结构语法；不复制冠饰、武器、装饰、角色配色或虚构性能。三张URI原图持续提供线条、材质、色彩与精密细节的层级。下肢保留厚实护罩、强关节与宽脚的粗比例；精确轮廓、尺寸和结构仍未冻结。

## 工程目标与分区

- 无人双足、双臂通用作业平台；约2.65 m为本项目初始高度目标，GD01官方完整尺寸尚未核到。
- 用户要求临时搬起/挪动数吨级重物。5 t只是代表检查工况；近身静止短行程、地面拾取、带载行走分别验证。没有货运车厢、驾驶舱或自动武器任务。
- 承力桥位于头体后方，肩部主轴/支架直接接主架与骨盆。面部/颅甲是感知与保护罩，不承受双手载荷。
- 头体前部提供光学窗口、轻量内部指向模块和遮挡保护；实际镜头视场、近焦和工作姿态遮挡要测。任务接触区可另设受保护腕部相机，不依赖胸前单一视角。
- 驱动、供能和冷却候选需共同布置；重载驱动优先比较工业电液与高力电驱。当前图不决定供货SKU、母线、电池量、压力、续航或整机重量。
- 腿的厚实外观由结构、驱动包络及分段轻质护罩形成；[粗腿初筛](leg_feasibility.md)给出数量级，不等于安装/运动通过。
- 工具手需确定实际指掌自由度、正向承托与锁持界面；几吨物体不能仅凭光滑侧面摩擦夹紧示意放行。救援工具通过受支持快换接口比较。
- 后部检修、能源拆换、管线服务余量、外部可触及急停及断能保持纳入真实装配。先前Q1里的开盖、电源与急停位置是历史探索，不能宣称与本图构成同版CAD。

## 从Goose迁移的经验

已成功读取用户指定的「导入 Goose 工作区资料」任务，并检查其实际工作树。可点击[相机安装检查点](/home/ethan/Projects/Sai_Rotbots/.scratch/goose_stage_three_four/robots/Goose_V0.1/design/camera_installation_checkpoint.md)、[夹取检查点](/home/ethan/Projects/Sai_Rotbots/.scratch/goose_stage_three_four/robots/Goose_V0.1/design/tip_grip_checkpoint.md)、[同版制造外观门槛](/home/ethan/Projects/Sai_Rotbots/.scratch/goose_stage_three_four/robots/Goose_V0.1/design/manufacturing_appearance_acceptance.md)。来源路径/哈希记录在[goose_reference_manifest.json](goose_reference_manifest.json)；任务工作树仍在演进，SHA标记读取时的文件状态。

本机应用的是工作方法：完整器件、接头和弯线要装得下；相机在真实任务姿态能看到目标；局部夹持、整机承重和连续任务不能互相替代；供电与下放回馈/热量一起闭合；最后使用同版CAD装配渲染真实外观。Goose的50 g有限仿真流程及未完成整机状态，不外推为本机数吨能力。

## 落地交接

实际工程项目目录为`/home/ethan/Projects/Sai_Rotbots`（用户称Sai_Robots）。此次只在Sai_Art保存设计源与说明，没有在对方活动工作树写入机器人、修改控制或训练接口，也没有创建MJCF/URDF/CAD。

后续在工程项目的`robots/<确定的robot_id>/design/concepts/`登记外观参考，设计与参数放`design/`，制造源放`cad/source/`，硬件资料放`hardware/`。机器人ID尚未确定。建模时逐件定义主架、关节轴、器件安装、护罩厚度与固定，再由同一套装配导出CAD、显示/碰撞几何和逐体质量/惯量。原画只提供外观意图，不能用图片比例填入物理参数。准入规则以该工程的`sai_robots_engineering_rules.md`为准。

## 当前目视检查

新图头面低于两侧肩部上缘，面部朝前且可辨；独立的大胸壳与外露长颈已取消；肩背、中央头体、短腹与骨盆形成新的紧凑组织。完整双腿、宽脚、精密关节和URI蓝/暖白/橙黄关系保留。新肩罩较饱满，工程上仍需确认驱动空间与所需外包络；少量细小边缘笔触不作为制造分件依据。审美仍待用户评价，不宣称已获认可。
