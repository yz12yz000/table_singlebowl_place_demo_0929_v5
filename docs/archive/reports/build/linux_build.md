> 历史归档：本文记录当时版本，命令、参数和状态可能已被后续功能替代。当前说明见 [资料索引](../../../README.md)；原路径 `docs/build/linux_build.md`。

# Linux 机器人电脑：编译与部署

适用于 Ubuntu 22.04 + ROS 2 Humble，假设项目放在 `~/robot_grasp_ws`。本项目是三个独立的 Python 包，`colcon build` 负责安装节点、配置和 launch；不会替你安装或启动 UR 驱动、相机、位置控制器、夹爪驱动。

## 1. 准备环境和 ROS 依赖

先确认已安装 ROS 2 Humble。将本项目的 `src`、`tests`、`tools`、`docs` 等复制到机器人电脑，不要复制其他电脑的 `build/install/log`。

```bash
source /opt/ros/humble/setup.bash
cd ~/robot_grasp_ws
sudo apt update
sudo apt install python3-colcon-common-extensions python3-rosdep python3-venv python3-pip
# 仅当这台电脑从未初始化 rosdep 时执行：sudo rosdep init
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro humble -y
```

如 UR 驱动或控制器在其他工作空间中，继续 source 那个工作空间的 `install/setup.bash`。现场已有的 `handControl2_ws` 也必须已经构建成功。

## 2. 准备视觉运行环境和模型

**当前机器人电脑直接复用 `/home/rob/yolovision_ws/.venv`，无需在 `robot_grasp_ws` 中新建或复制虚拟环境。** 虚拟环境所在目录不限制它服务哪个项目；保留原目录，不要移动或删除。

```bash
source /opt/ros/humble/setup.bash
source /home/rob/yolovision_ws/.venv/bin/activate
which python
python -c "import rclpy, cv_bridge, numpy, cv2, ultralytics, openvino; print('依赖导入正常')"
```

现场已确认上述六个依赖导入正常，可以继续使用该环境构建和运行本项目；实际模型推理仍需后续测试。Ultralytics 的 settings reset 黄色提示不表示导入失败；如曾自定义其设置，再核对这些设置即可。不要仅为本项目重新安装或升级已有视觉依赖。

**以下仅供没有现成环境时备用，当前这台电脑跳过：** 使用基于系统 Python 的独立环境，不使用与 ROS Python 不匹配的 Conda 环境。

```bash
/usr/bin/python3 -m venv --system-site-packages ~/robot_grasp_venv
source ~/robot_grasp_venv/bin/activate
python -m pip install 'numpy<2' ultralytics openvino
python -c "import rclpy, cv_bridge, numpy, cv2, ultralytics, openvino; print('imports OK')"
python -m pip check
```

备用方案限制 NumPy 主版本，是为减少 Humble 系统二进制扩展的兼容问题，不要求修改当前已通过导入检查的环境。如果依赖解析或导入失败，先解决版本冲突，不能直接忽略；新装的视觉版本仍需用实际模型验证。

项目使用源码目录 `src/yolo_vision/yolo26n-seg_openvino_model` 中已有的 OpenVINO 分割模型（包括 XML/BIN 及模型元数据）；构建时该目录会安装到 package share。项目不会自动下载或重新导出模型。

## 3. 检查源码并构建三个包

在上述环境的同一终端运行：

```bash
cd ~/robot_grasp_ws
python -B tools/check_source.py
python -B -m unittest discover -s tests -v
colcon list
python -m colcon build --symlink-install --packages-select yolo_vision rim_locator grasp_executor
source install/setup.bash
ros2 pkg executables yolo_vision
ros2 pkg executables rim_locator
ros2 pkg executables grasp_executor
```

通过标准：源码检查通过、单元测试全部通过、三个包构建成功、三个包都能列出可执行入口。使用 `python -m colcon` 是为了让节点安装入口使用当前视觉环境的 Python。离线单元测试不会控制机器人。

## 4. 保存现场配置

```bash
mkdir -p ~/robot_grasp_config
cp src/yolo_vision/config/config.json ~/robot_grasp_config/yolo.json
cp src/rim_locator/config/config.json ~/robot_grasp_config/rim.json
cp src/grasp_executor/config/config.json ~/robot_grasp_config/grasp.json
```

只在首次部署时复制，后续不要覆盖已经标定的现场配置。

- `yolo.json`：模型绝对路径、RGB/点云 Topic、实际图像尺寸；点云必须是与 RGB 像素对齐的有序点云。
- `rim.json`：目标坐标系应为 `base_link`。
- `grasp.json`：填写朝下姿态、夹持偏移、工作范围和夹爪 setup 路径。执行器没有额外的标定确认开关，启动前必须人工核对这些值。

## 5. 新终端加载环境，先启动感知

每个运行终端都加载 ROS、现场依赖工作空间、Python 环境及本项目环境：

```bash
source /opt/ros/humble/setup.bash
# 如有自建 UR/控制器工作空间，在这里 source 其 install/setup.bash
source /home/rob/yolovision_ws/.venv/bin/activate
source ~/robot_grasp_ws/install/setup.bash
ros2 launch grasp_executor pipeline.launch.py enable_grasp:=false \
  yolo_vision_config:=$HOME/robot_grasp_config/yolo.json \
  rim_locator_config:=$HOME/robot_grasp_config/rim.json
```

每次打开新终端都需要重新加载以上环境；仅在使用备用新环境时，将 activate 路径换成 `~/robot_grasp_venv/bin/activate`。项目尚未构建成功时，先完成第 3 步，再加载项目的 `install/setup.bash`。

先启动现场相机、机器人状态和 TF，再运行以上命令。此命令不启动抓取节点。后续按 [上机检查与首次测试](robot_test_checklist.md) 操作。

常见问题：找不到包通常是未 source 正确的 install；找不到模型通常是路径仍指向 Windows 或默认目录；仅构建成功不代表模型、控制器和夹爪能运行。修改 Python/安装文件后重新构建；上述外部 JSON 修改后重启相应节点即可。

参考：[ROS 2 Humble 构建工作空间](https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Colcon-Tutorial.html)、[Ultralytics OpenVINO](https://docs.ultralytics.com/integrations/openvino/)。
