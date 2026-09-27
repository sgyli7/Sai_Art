# Sai_Art 维护入口

- 新资产、制作工具或路径迁移前，读 [资产规则](art_engineering_rules.md) 和 [目录导航](docs/repository_layout.md)，确认制作源与导出副本。
- 跨仓库运行/资产/副本维护按规则中指向的 Lab 职责约定执行；Lab 缺失时继续本地资产工作，运行迁移保持原状。
- 原位修复既有文件不要求顺带迁移。活动 Tick 工作、现有运行/启动、共享产物在本轮目录整理中保持原状。
- 明确实现型委派使用 `cursor-grok` skill 的单次前台调用；物理/RL 结论与 observation/action contract 由主 Agent 判断。
