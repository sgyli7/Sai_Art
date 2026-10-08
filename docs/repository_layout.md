# Sai_Art 目录导航

## 项目导航

| 项目 | 浏览入口 | 制作源与历史 |
| --- | --- | --- |
| **Gorilla V0.2** | [设定集](../robots/gorilla/README.md)、[五款四视图](../robots/gorilla/artbook.md)、[B7 3D 与交付包](../robots/gorilla/README.md#3d-资产与交付包) | [V0.2 制作源](uri_style/gorilla_v0_2/README.md)、[V0.1 历史](uri_style/gorilla_v0_1/README.md) |
| Sainiverse V0.1 | [载具资料与演示](../vehicles/Sainiverse_v0.1/README.md) | `vehicles/Sainiverse_v0.1/` |

Gorilla 当前交付集中在 `robots/gorilla/v0_2_p30/`，是冻结 P30 包的逐字节浏览副本。原始制作和迭代仍在 `docs/uri_style/gorilla_v0_1/` 与 `gorilla_v0_2/`，保留旧脚本与共享交付引用；设定集默认指向 P30，旧 AA3、S 系列与 P22 等放在历史导航中。模型、归档 ZIP 和大型几何数组使用 Git LFS，图片和设定文档可直接在 GitHub 浏览。


资产新增或迁移按 [本地规则](../art_engineering_rules.md)。跨仓库职责维护源位于 Sai_Lab `Godot_Sim2Sim/docs/repository_ownership.md`（本地检出根可用 `SAI_LAB_ROOT` 指定）。缺少 Lab 时资产工作继续；本导航描述当前交付，不表示运行代码已迁走。

| 当前位置 | 角色 / 维护方式 |
|---|---|
| `vehicles/Sainiverse_v0.1/source` | 建模、导出、纹理与几何验证源；混有 launch/任务验证等运行相关代码，保持路径、按清单分开登记 |
| `vehicles/Sainiverse_v0.1/assets` / `themes` | 资产导出、贴图与主题；部分 shader 是历史引擎副本，不能因目录名就当作制作源 |
| `vehicles/Sainiverse_v0.1/physics` / `bindings.json` | 已验证交付数据与绑定；保持值和路径，后续以交付约定消费 |
| `vehicles/Sainiverse_v0.1/runtime` | 载具、登船、镜头、UI 与机构运行实现；未来维护源归 Lab，本轮兼容保留 |
| `vehicles/Sainiverse_v0.1/support` | 历史制作工具、设计诊断、运行脚本、原生库混合；按职责分别识别，不能整目录删掉 |
| `vehicles/Sainiverse_v0.1/baseline` / 载具 docs | 设计/物理基底与交付说明；保留原始路径和来源 |
| `integration/robots` | 原机器人快照、模型/策略/原生库及后加覆盖；来源 manifest 原样保留 |
| `integration/sai60` | 新 60 Hz 机器人运行及策略交付；Tick 工作保护区，本轮保留 |
| `integration/review_project.godot` | 现有集成配置；保持组装方式 |
| `run.py` | 资产展开、快照复制、游戏机器人同步、覆盖与启动的历史统一入口；不执行、不拆分 |
| `tests` | 现有游戏交互/接触等检查保留；新资产几何/导出验证可在此维护 |
| `docs` / `evidence` | 制作、许可、验证说明和复现证据；冻结证据原位保留 |
| `requirements.txt`、根 README、忽略与版本文件 | 现有环境和导航；不增加构建前置依赖 |
| `.runtime` / `.venv` / 展开的 blend | 本机生成或展开产物，使用对应制作源重建 |

## 组装来源

Lab 的 Sainiverse 启动器调用 Art `run.py`。它先展开 `vehicles/Sainiverse_v0.1` 到 Art `.runtime`，按现有标记将 Art 机器人快照复制到游戏 review runtime，并刷新 carrier_worker；再可选读取 Lab `results/workshop-hub/runtime` 和 Godot 源码，执行既有文本兼容转换，叠加可选 Sai60，最后安装 Art avatar 样式。清单 `assembly` 记录入口版本、转换和顺序，实际执行仍以原 `run.py` 为准；不能拿旧快照 manifest 声称覆盖后内容仍完全一致。

具体基线、角色与副本来源见 [清单](directory_inventory.json)。逐文件比较的维护记录位于 Lab 的 `Godot_Sim2Sim/docs/directory_inventory.json`，注明双方提交及 SHA256；实时工作目录可能已有新的修改。

## 后续任务

先选择制作源或兼容角色，再新增内容。新正式运行功能进入 Lab；新增旧布局兼容文件必须有精确路径和原因。原位修复既有文件、制作资产、运行既有验证不以“清完所有旧目录”为前提。

本轮轻量检查需 Lab 时用显式检出路径调用；没有 Lab 则按本地规则人工检查，不自动下载、同步或启动游戏。
