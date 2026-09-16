# Sainiverse_v0.1

私有设计审阅版：可编辑车体、四套主题、MuJoCo 模型和 Godot/Jolt 可驾驶版本。沿用现有 Robot_Godot_Sim2Sim 工程，英文显示名统一为 **Sainiverse_v0.1**。

## 实际仿真演示

以下均来自实际物理仿真。每段约 10 秒；画面标注原始仿真时间。

**起伏丘陵：直行、上坡、转弯与下坡**

![Sainiverse_v0.1 — hills and steering](evidence/media/Sainiverse_v0.1_hills.gif)

**Sai：从地面经坡板登上升降台，再驶入甲板**

![Sainiverse_v0.1 — Sai boarding](evidence/media/Sainiverse_v0.1_sai_boarding.gif)

完整登车流程约 99 秒；这段选取坡板、登台、升降和离台四个阶段。为匹配 Sai 的 2 kHz 控制，车体先动态静置 10 秒，再作为固定支承；升降台、坡板和机器人仍参与实际受力与碰撞。另有完整动态车体的 500 kg 升降测试。

**MicroDuck 行走模式：驾驶舱巡视**

![Sainiverse_v0.1 — cockpit patrol](evidence/media/Sainiverse_v0.1_cabin_patrol.gif)

**驻车作业：八台吊机、天线板与轮滑 MicroDuck**

![Sainiverse_v0.1 — worksite and deck patrol](evidence/media/Sainiverse_v0.1_worksite.gif)

角落近景与全景来自同一时刻、同一物理世界。吊机演示为空载机构动作；尚未完成外部货物的起吊载荷验证。

## 打开可驾驶版本

需要现有 **Robot_Godot_Sim2Sim** checkout、Godot 4.7 / Jolt。附带原生扩展适用于 **Linux ARM64**；其他平台需重建扩展。机器人使用已有 ONNX 策略，车辆采用有限力控制器；任务调度不是新训练出的端到端策略。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py --game /absolute/path/to/Robot_Godot_Sim2Sim/main
```

Godot 不在 PATH 时设置 `GODOT_BIN`。首次启动会将演示所需机器人资源装入现有工程的 review runtime，并进行导入；不会创建新的游戏项目。展开后的绝对路径放在忽略的 `.runtime/` 目录。

- W/S 驾驶，A/D 转向，Shift+W 请求高速，空格制动。
- Tab 切换视角；右键环视、滚轮缩放；自由视角 WASD、Q/E。
- G 选择升降台，L 升降，Shift+L 全部；升降台和作业机构未收妥时禁止行驶。
- C 作业/收起，N 选择吊机；小键盘 4/6 回转、8/2 俯仰、+/− 伸缩；PageUp/PageDown 卷扬。
- Z/X 天线回转，R/F 折叠；O 舱门；T 切换黑色/沙漠/白色/蓝色；F12 截图。

```bash
# 手动崎岖地形试车
.venv/bin/python run.py --game /path/to/main --terrain hills
# 复现四个任务
.venv/bin/python run.py --game /path/to/main --mode hill_turn --terrain hills --seconds 55
.venv/bin/python run.py --game /path/to/main --mode sai_board --seconds 115
.venv/bin/python run.py --game /path/to/main --mode cabin_patrol --seconds 24
.venv/bin/python run.py --game /path/to/main --mode worksite --seconds 43
# MuJoCo 机构检查与解压 Blender 源文件
.venv/bin/python run.py --action mujoco
.venv/bin/python run.py --action equipment-mujoco
.venv/bin/python run.py --action unpack-blend
```

## 本次结构修正

平台红色腰线与侧面共用同一表面；驾驶舱通过落地支座、斜撑和下部纵梁接入甲板。底部补入配电/传动分工，冷却管采用连通弯管。六个升降台具有实际坡板和登台桥；设备间两侧配有对应窗户。普通颜色按物理部件合并绘制，保留手绘贴图、法线细节和独立主题。

可编辑 Blender、命名刚体 GLB、贴图生成源与 MJCF 在 [`vehicles/Sainiverse_v0.1/`](vehicles/Sainiverse_v0.1/)。机器人运行依赖及来源记录在 [`integration/robots/`](integration/robots/)。测量条件、性能、功能边界和具体证据见 [验证记录](docs/VALIDATION.md)。

这是仿真设计审阅版。质量、壁厚、液压能力和强度仍为工程假设；已运行的测试不等同于实体制造认证。第三方素材与机器人模型保留各自来源和许可，详见 [运行依赖说明](integration/robots/licenses/README.md)。
