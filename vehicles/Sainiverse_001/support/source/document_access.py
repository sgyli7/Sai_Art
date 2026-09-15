"""Record only measured final candidate results after acceptance checks."""
import json
from suspension_physics import ROOT

def main():
    out=ROOT/'candidates/r025_access';v=json.loads((out/'reports/access_validation.json').read_text());assert v['passed'];rough=v['performance']['access_whole_latch_v2_180'];high=v['performance']['access_high100_latch_v2_180'];pair=v['paired_engines']
    text=f'''## 最终运行测量

1080p / NVIDIA GB10 / 阴影 / 4MSAA / 200Hz，完整模型、当前着色和门/墙/窗碰撞，均为独立无截图180秒运行（去显示统计前三秒，包含加速）：

| 路况 | 中位FPS | p95帧耗时 | 仿真/墙钟比 | 最高速度 |
|---|---:|---:|---:|---:|
| 起伏路后平地 | {rough['median_fps']:.2f} | {rough['p95_frame_ms']:.3f}ms | {rough['simulation_wall_ratio']:.6f} | {rough['peak_speed_kmh']:.5f}km/h |
| 100km/h直线 | {high['median_fps']:.2f} | {high['p95_frame_ms']:.3f}ms | {high['simulation_wall_ratio']:.6f} | {high['peak_speed_kmh']:.5f}km/h |

最终两引擎门循环最大门角差{pair['maximum_door_angle_difference_rad']:.6f}rad，车体位置RMSE{pair['hull_positions_rmse']*1000:.3f}mm、速度RMSE{pair['speed_m_s_rmse']:.6f}m/s。两引擎起伏和高速样本保持上锁且未误触发行驶联锁。性能仅覆盖当前整车台架；真正机器人和吊装任务、科研站主场景负载尚未计入。
'''
    p=out/'README.md';s=p.read_text();s=s.split('## 最终运行测量')[0].rstrip()+'\n\n'+text;p.write_text(s)
    progress=ROOT.parent.parent/'docs/PROGRESS.md';s=progress.read_text();heading='## 2026-09-15 · Leviathan003 r025 实际舱门与门锁'
    assert heading not in s
    progress.write_text(s+'\n\n'+heading+'''

保持驾驶→集装箱→能源、两节33×27m及r024白色主色/原22色。完整22755件、1369164三角面、156网格、27组；六扇独立物理门，实际同侧共轴铰链/驱动外形与远轴锁。可编辑Blender、中性GLB、完整物理输入保存。80kg/门及包围盒惯量暂定，新增480kg总15260480kg；159体164DOF26驱动、Godot158关节，非质量账或硬件资格闭合。

新增306凸舱壁、11固定窗、24移动门/把手/锁形状，加原35地板共376接触形状。父子接触打开，门洞空腔保留。单精度分块核对失败后改双精度，漏体积2.372e-5m³/多7.939e-6m³；失败源/几何保存。全部刚性门件0–110°连续区间几何净空证明，软密封显式排除；相邻独立门扫掠X间隔至少0.126m。实际开门几何下Sai/MicroDuck各261包络位置通过中央通道、首组双侧门、工作台接近及完整足迹支撑；非真实登车策略。

双引擎各45秒实际门循环及3×71墙/窗/门洞射线通过，关闭命中门、打开净空；另32地板射线通过。开门120Nm/关门25Nm/100W单门有限驱动。首个整车起伏长测仅电机保持会偏2°/联锁误触发，原96.86FPS样本保留。增加独立被动有限门锁；首个软锁仍误触发，输入/诊断保留。最终200kNm/rad、2500Nms/rad、1500Nm上限，停车开门解锁，关门小角/低速捕获；不是无限锁死或扩大电机功率。夹阻分支未作接触力安全资格测试。

'''+text+'''
当前完整候选为vehicles/Leviathan_003/candidates/r025_access，README/数值验收/图像/失败/源快照/哈希齐备。已查看原生实际开门细节和Blender结构图，152原色材质误差5.96e-8、72动态描边状态匹配。运行临时项目设置恢复原字节，正式r014入口未替换。

全目标继续未完成。升降/真实机器人上下车、移动载具作业、吊装/货物、主场景集成仍缺；早期双模块7.45m升降预留不适用于当前三模块11.35m舱内，应重新布置。旧主悬挂、履带接触/松垂/脱轨、硬件及高速操纵资格边界保留。未标记目标完成或阻塞。
''')
    print('README and PROGRESS updated')
if __name__=='__main__':main()
