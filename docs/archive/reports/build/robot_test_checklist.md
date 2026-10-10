> 历史归档：本文记录当时版本，命令、参数和状态可能已被后续功能替代。当前说明见 [资料索引](../../../README.md)；原路径 `docs/build/robot_test_checklist.md`。

# 上机检查与首次测试：一个碗、一个目标点

先完成 [Linux 编译与部署](linux_build.md)。本版执行“接近 → 打开夹爪 → 竖直下降 → 关闭夹爪”，不抬升、不放置、不自动重试。按以下顺序逐项通过后再进行实机抓取。

每个新测试终端按部署文档加载 ROS 和现场依赖工作空间，再执行 `source /home/rob/yolovision_ws/.venv/bin/activate`、`source ~/robot_grasp_ws/install/setup.bash`。直接复用原虚拟环境，不需要在本项目内新建或复制 `.venv`。

## 1. 核对真机接口（只读）

使用现场已有方式启动 UR 驱动、相机、夹爪所需驱动和 TF，检查机器人处于可控状态。再运行：

```bash
ros2 control list_controllers
ros2 param get /cartesian_motion_controller robot_base_link
ros2 param get /cartesian_motion_controller end_effector_link
ros2 topic info /cartesian_motion_controller/target_frame -v
ros2 run tf2_ros tf2_echo base_link grasp_center
```

应确认：

- `cartesian_motion_controller` 为 `active`，基座参数为 `base_link`，目标 Topic 类型为 `geometry_msgs/msg/PoseStamped`，有控制器订阅。
- 实际末端参数对应的坐标系到 `grasp_center` 存在固定工具 TF；程序默认 `controller_tip_frame=auto`，会读取并换算。
- `base_link → grasp_center` 实时更新；相机点云坐标系到 `base_link` 连通且外参正确，基座 Z 轴向上。
- 没有其他程序同时向目标 Topic 发送命令。控制器名称或命名空间不同，应修改抓取配置中的对应字段。

## 2. 填写现场标定值

编辑 `~/robot_grasp_config/grasp.json`：

| 字段 | 填写和检验方法 |
|---|---|
| `fixed_orientation` | 人工将夹爪摆到适合抓碗的朝下姿态，读取上面的 TF 四元数 `[x,y,z,w]`，对应填写；不是欧拉角。 |
| `grasp_offset` | 从视觉碗沿点到所需夹持中心的修正，沿 `base_link` XYZ，单位米。不要重复填写工具长度，工具偏移已由 TF 换算。 |
| `workspace_min/max` | 现场允许的夹爪中心范围，单位米，包含当前起点、接近点和抓取点；它不是整条机械臂的避障范围。 |
| `approach_height` | 碗沿上方的接近高度，单位米，确认夹爪和碗有足够空间。 |
| `hand_control_setup` | 实际夹爪工作空间的 `install/setup.bash` 路径。 |

可用以下命令只预览位姿，不发机器人命令。把 `X Y Z` 替换成实际目标坐标：

```bash
ros2 run grasp_executor preview_grasp --config "$HOME/robot_grasp_config/grasp.json" --point X Y Z
```

应看到接近点与抓取点 XY 相同，接近点 Z 高出 `approach_height`，姿态符合预期，位置在允许范围内。当前默认四元数、零偏移和宽范围不能直接视为已标定。

## 3. 先检查感知，不启动抓取

运行第一份文档中 `enable_grasp:=false` 的启动命令，只摆一个碗。用 RViz（Fixed Frame 为 `base_link`）和图像查看器检查：

| 模块 | 需要看到的结果 |
|---|---|
| `yolo_vision` | overlay/mask 只选中目标碗；`/yolo_vision/object_cloud` 是碗的点云，无明显背景混入。RGB 和点云必须像素对齐，不能只看尺寸一样。 |
| `rim_locator` | `/rim_locator/rim_point` 位于实际碗沿近侧，单位为米、坐标系为 `base_link`；检查中间点云，不能把上方杂点识别成碗沿。 |

分别调试时可单独启动：

```bash
ros2 launch yolo_vision yolo_vision.launch.py config_path:=$HOME/robot_grasp_config/yolo.json
ros2 launch rim_locator rim_locator.launch.py config_path:=$HOME/robot_grasp_config/rim.json
```

以上是替代总启动的方式，不要重复运行同名节点。定位节点可先启动以等待视觉输出；两个节点都是单次处理，重测需重启。任一状态为 `failed` 时先处理原因。

## 4. 检查夹爪，再做一次实机抓取

在夹爪周围无夹伤风险、碗不会掉落的条件下，单独验证现场 `hand_control talker Open 1` 和 `Close 1`：确实开合，且命令在 `gripper_timeout`（默认 5 秒）内成功退出。仅返回码成功不能证明夹牢。

确认接近和下降路径无碰撞、机器人端采用适合首次测试的低速设置、操作者可及时停止机器人。程序的参考速度不是本体硬限速，也没有避障规划。

退出之前的感知节点和测试目标发布器，防止旧的保留目标被新节点接收；人工确认现场配置和路径后，启动一次全流程：

```bash
ros2 launch grasp_executor pipeline.launch.py \
  yolo_vision_config:=$HOME/robot_grasp_config/yolo.json \
  rim_locator_config:=$HOME/robot_grasp_config/rim.json \
  grasp_executor_config:=$HOME/robot_grasp_config/grasp.json
```

**此命令会在检测到合格目标后自动触发真实机械臂动作，没有额外的执行确认按钮。** 应在输入等待时间内提供相机数据，并保持 `use_sim_time=false`。

观察状态：

```bash
ros2 topic echo /grasp_executor/status std_msgs/msg/String --qos-reliability reliable --qos-durability transient_local
```

通过标准：接近位置正确 → 夹爪打开 → 下降时 XY 基本保持不变 → 到抓取点关闭 → 状态成功；现场再确认没有碰撞、夹持位置正确。成功后保持最终目标，不会自动抬碗。

## 5. 失败时检查什么

- 预检查或重复目标拒绝：应没有运动命令，也不应停用控制器。
- 已发出运动命令后失败：检查失败原因和 `stop_error`，并核对控制器是否已停用；停用确认不等于物理急停验证。
- 旧目标拒绝：重启感知获取新的观测；不要清空去重记录来强行重复旧任务。
- 运动失败后先确认实际位置、原因和现场状态，再人工重新准备控制器。不要用拔掉 TF 等方式在首次实机抓取中故意制造故障。

去重和异常分支先用 `python -B -m unittest discover -s tests -v` 做离线回归。现场保存状态日志、三个实际配置和软件版本，便于复现问题。当前源码检查和离线测试不代表已经通过 ROS/真机验收。
