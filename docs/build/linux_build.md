# 构建与部署

本工作区位于 `/home/rob/robot_grasp_0929demo`，包含三个 ROS 2 Humble Python 包：`yolo_vision`、`rim_locator`、`grasp_executor`。迁移时保留根目录启动脚本、`src/`、`tools/`、`New_run/` 和当前文档；构建输出需在目标机器重新生成。

## 环境与构建

现有启动脚本使用 `/usr/bin/python3`。确认这个解释器能导入 ROS 与视觉依赖，再在已加载 ROS 和现场依赖的终端构建：

```bash
source /opt/ros/humble/setup.bash
source /home/rob/ws_moveit2/install/setup.bash
source /home/rob/ur_ros2_ws/install/setup.bash
source /home/rob/ur_sim_ws/install/setup.bash
cd /home/rob/robot_grasp_0929demo
/usr/bin/python3 -c 'import rclpy, cv_bridge, numpy, cv2, ultralytics, openvino'
colcon build --symlink-install --packages-select yolo_vision rim_locator grasp_executor
source install/setup.bash
ros2 pkg executables yolo_vision
ros2 pkg executables rim_locator
ros2 pkg executables grasp_executor
```

外部工作区位置不同则调整路径，启动时也通过 `MOVEIT_WS`、`UR_DRIVER_WS`、`UR_MODEL_WS` 等变量保持一致。项目复用已有依赖和 OpenVINO 模型，不在构建中自动下载或重新导出模型。

## 离线验证

```bash
./run_pipeline_place_offline_test.sh
```

该入口会构建三个包，运行单元测试、隔离 ROS 接口和模拟 MoveIt 检查，不启动相机或硬件驱动。运行会正常产生构建和测试输出。

仅运行相关纯 Python 测试时：

```bash
PYTHONPATH="$PWD/src/grasp_executor:$PWD/src/rim_locator:$PWD/src/yolo_vision:$PWD/tools"   /usr/bin/python3 -B -m pytest -q src/grasp_executor/test src/rim_locator/test src/yolo_vision/test   tools/test_place_rounds.py tools/test_place_runner.py
```

历史归档中的源码及测试快照不属于现行测试集，按上述路径运行测试。

## 配置与现场运行

完整 place 配置分别位于三个包的 `config/place_config.json`；六点及固定起点位于 `src/grasp_executor/config/place_zones.json`。这些文件已有现场参数，部署时保留，不用通用 `config.json` 覆盖。

视觉配置可用 `--vision-config 文件` 覆盖，目标配置可用 `--place-zones-config 文件` 指定；路径相对调用终端解析。修改模型路径、工具帧、ROI 或示教位置后需核对现场数据。相机、UR、夹爪等外部驱动不由 colcon 自动安装。

构建成功后按 [启动顺序](../startup.md) 和 [上机检查](robot_test_checklist.md) 操作。旧部署说明见 [历史归档](../archive/README.md)。
