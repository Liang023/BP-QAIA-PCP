# 最终版本验证记录

2026-09-22，基于上游提交 `231fe9c9c744d679ded0c6d121d79e2b4a032ad0`。

## 环境

- Linux，Python 3.10.21
- MindQuantum 0.11.0（仓库本地 qaia 实现仍保留）
- Optuna 4.9.0
- Gurobi 13.0.3，小模型许可可运行
- NumPy 2.2.6，SciPy 1.15.3

Windows 移动云 SDK 未在此环境安装；不把本地 mock 测试当作真机验收。

## 自动测试

`python -m pytest -q`：26 项通过。

覆盖既有模型等价性、约化成本、解校验、anytime 轨迹、primal completion；新增冻结参数 xi 传递、可行性优先调参评分、CIM 构造接口不兼容提示、实际 QUBO 表达式枚举检查、原精度能量排序、二进制解码、超时/请求上限/规模上限及修复。CIM 测试使用 mock，不发送网络请求。

## 实际本地运行

在 v1_N6_C2_s0 上运行两次 Optuna trial、训练种子 0、每次 3 秒预算：

- trial 0：200 次迭代、batch 10、dt=1、xi=auto，最优目标 6。
- trial 1：500 次迭代、batch 4、dt≈1.18568、xi≈0.66234，最优目标 6。
- 离线调参时间约 4.824 秒，生成 best_qaia.json。

新进程读取冻结配置后，在同一小实例运行 5 组：

| 方法 | 状态 | 目标 | 本次 wall_seconds（约） | tuning_seconds_in_bp |
| --- | --- | ---: | ---: | ---: |
| Compact | optimal | 6 | 0.0085 | 0 |
| Exact | optimal | 6 | 0.0447 | 0 |
| Greedy10 | optimal | 6 | 0.0309 | 0 |
| 默认 QAIA | optimal | 6 | 0.0696 | 0 |
| 冻结 QAIA | optimal | 6 | 0.0845 | 0 |

这是功能与计时分离验证，既没有足够重复，也没有独立测试实例，不能用于方法优劣结论。两种参数均最优不证明调参收益。

另外以 CIM_MAX_CALLS=0 运行 cim_root：Exact 回退得到目标 6；CIM requests=0、completed=0、capped_skips=10。这只验证禁用请求后的流程，不是 CIM 成功求解。

summarize_scale 和 compare_anytime 均已成功读取上述五组批量记录并输出报告。

## 数据流程

使用原始 260 条 ACN 记录执行 inspect_acn_dates 的 train 划分，确认五个日期有效车辆数为 37、37、37、42、35。使用 prepare_scale 生成 03-04 的 N16/C4 和 N16/C2 两实例，各 333 个候选顶点，审计和 manifest 正常生成。

新提出的验证/测试日期尚未下载，未声称其有效车辆数或模型难度已经得到验证。CIM 实际云端延迟、SDK 版本兼容性及真机解质量需在用户环境完成单任务试点。
