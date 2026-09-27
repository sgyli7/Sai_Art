# Sai_Art 资产维护规则

本文件约束新资产、制作工具与目录迁移。现有文件原位修改不要求顺带搬迁、改名或格式化。目录导航和保留原因见 `docs/repository_layout.md` 与 `docs/directory_inventory.json`。

## 制作与落点

- 可编辑模型、图片、主题、贴纸、资产动画，以及建模/裁剪/导出/几何验证工具在 Art 维护。文件语言不是职责判断依据：Blender/Python/设计预览代码属于资产制作。
- 新载具内容按需放入 `vehicles/<vehicle>/source`（制作源与工具）、`assets`（导出资产）、`themes`（主题）或 `docs`（交付说明）；通用制作工具放 `scripts`，几何/资产验证放 `tests`，说明和清单放 `docs`。不预建空目录。
- 新自研文件主名使用 snake_case；既有载具标识、上游名称、导入附属文件与许可文件保持约定名称，确需新增特殊名称时登记精确文件和原因。
- 保留资产坐标系、单位、节点/骨架名与碰撞代理关系；未经单独验证不改质量、惯量、关节和碰撞数值。

## 运行与副本

正式游戏的控制器、物理后端、ONNX 部署、UI、镜头、任务、引擎 shader 和启动组装维护源为 Sai_Lab。Art 新运行文件、策略或原生运行库只允许作为登记过来源的交付副本/兼容文件，不发展第二套活动实现。

`integration/robots` 是带上游来源的历史机器人快照及后加覆盖，`integration/sai60` 和载具 runtime/support 中的运行代码暂保留。原 manifest、基线、许可和 evidence 不回写、不批量删除。修复尚未迁移的兼容代码时记录维护来源和差异，不要求先完成迁移。

新旧布局兼容文件在清单 `compatibility_additions` 登记精确路径、原因；导入副本在 `source_records` 登记精确文件、来源仓库、版本、SHA256。文件类型/路径检查不代替职责和验证审查。

## 跨仓库约定与检查

唯一跨仓库职责维护源是 Sai_Lab 的 `Godot_Sim2Sim/docs/repository_ownership.md`。本地可通过 `SAI_LAB_ROOT` 指向检出根；发布后的 [规范地址](https://github.com/sgyli7/Sai_Lab/blob/main/Godot_Sim2Sim/docs/repository_ownership.md)供查阅。该链接随两仓库整理分支合入后可用。

Lab 缺失时继续按本地资产规则制作和验证；跨仓库运行迁移保持原状。Lab 可用时，可手动执行其 `Godot_Sim2Sim/scripts/check_godot_structure.py --repo-root /path/to/Sai_Art`；不可用时人工检查新增路径与登记内容。资产制作本身没有新的 Lab/网络/检查工具前置依赖。

后续单个任务可加 `--base <任务起点提交>`；只核查相对该提交新增/搬移的路径，相对于比较点的已有文件内容修改跳过，历史分叉与缺失可选 peer 只提示。

本轮目录整理在隔离 worktree 中进行，保留活动 Tick 工作、Art 运行/启动修改、共享 `.runtime`、实验和缓存。普通业务授权与本轮整理范围分别判断。这轮不运行 run.py、准备/安装/构建/启动，也不改变 hooks、CI 或既有路径。
