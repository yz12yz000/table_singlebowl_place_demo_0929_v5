# 当前单碗抓放上机检查

先完成 [构建与部署](linux_build.md)，再按 [启动顺序](../startup.md) 操作。当前完整入口包含抬升、放置和返回起点，预览与真实执行分别使用独立脚本。

1. 核对当前机械臂、夹爪、相机和坐标系；准备脚本已就绪，已有驱动不重复启动。
2. 在示教器运行包含 External Control 的程序，再执行 `./run_grasp_position_control.sh --check` 检查控制条件。
3. 核对 [当前放置点](../当前放置点.md) 和 [当前起始点](../当前起始点.md)，程序目标以 `place_zones.json` 为准。六点下降距离均为 0.122 m。
4. 桌上只放一只碗，确认 RGB、对齐深度和 CameraInfo 正常；相机或桌子移动后重新核对 ROI 和标定。
5. 独立运行 `./run_pipeline_place_test.sh --target-zone 左上`，检查七段规划结果、目标参数快照和候选投影图。预览通过只证明路径可规划。
6. 现场确认后独立运行 `./run_pipeline_place_execute.sh --target-zone 左上`。确认夹爪开合、物体实际抓牢与释放、上退以及返程结果；一轮结束后再开始下一轮。
7. 失败或保护停机时检查本轮结果和日志，不用历史成功记录替代本轮验收。只有释放、上退和返程均完成才会报告任务成功。

其他目标逐个独立检查，不在一条命令中自动轮流测试。`grasp_verified` 与 `placement_verified` 仍为 false，需要现场检查物体结果。现有碰撞检查不含未建模桌面。

日志默认位于 `debug_output/place_validation/` 或 `debug_output/place_execution/`。当前参数、夹爪稳定反馈和单独返程条件见 [完整抓放说明](../../New_run/README.md)。旧 FZI 上机清单见 [历史归档](../archive/README.md)。
