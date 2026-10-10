# 机器人单碗抓放工作区

当前入口每次处理一只碗，完成抓取、放置、释放、上退和返回固定起点后退出。目标支持左上、左下、中间、右上、右下、blue，或完整的 XYZ 释放坐标。

- [启动顺序与控制模式](docs/startup.md)
- [完整抓放参数与日志](New_run/README.md)
- [模块、接口与当前资料索引](docs/README.md)
- [构建与部署](docs/build/linux_build.md)
- [上机检查](docs/build/robot_test_checklist.md)
- [历史资料与归档清单](docs/archive/README.md)

在项目根目录运行：

```bash
./run_pipeline_place_test.sh --target-zone 左上
# 完成现场检查后，独立运行一次真实抓放：
./run_pipeline_place_execute.sh --target-zone 左上
```

根目录脚本是实际入口，`New_run/` 中的同名脚本转发到根目录。现行代码在 `src/` 和 `tools/`；重复脚本、旧控制后端和旧方案已集中归档。历史记录不代表当前参数或已完成实机验收。
