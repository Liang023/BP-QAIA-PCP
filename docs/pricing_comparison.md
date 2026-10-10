# 同一定价任务与采样／修复贡献对照

入口：`python -m run.pricing_compare {collect,replay,summarize}`。本轮保持论文及 `results/result_c5_v1` 不变，不运行完整 1800 秒算法实验。所有输出目录必须是新目录，禁止覆盖已有逐次记录。

## Windows PowerShell 命令

先设置一次工作目录、Python 和新的结果目录。以下使用本项目已有的 Python 环境；如本机路径不同，替换 `$Python`。

```powershell
Set-Location 'D:\pythonProject\BP_QAIA_PCP'
$Python = 'E:\Miniconda\envs\py3.10\python.exe'
$Batch = 'results\pricing_comparison_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
```

A. 采集最多 6 个独立根节点定价快照；每个算例最大 60 秒，达到 6 个立即退出。根节点可用任务不足时继续下一算例；根节点完成后不探索子节点。采集固定使用已有 `provider="greedy"`，不会访问 CIM。若全部算例仍不足 6 个，保留失败／不足记录并以非零状态结束；不要继续 C。

```powershell
& $Python -m run.pricing_compare collect `
  --instance data/instances/2019-03-12_N10_C5.json `
  --instance data/instances/2019-03-12_N20_C5.json `
  --instance data/instances/2019-03-18_N10_C5.json `
  --instance data/instances/2019-03-18_N20_C5.json `
  --instance data/instances/2019-03-20_N10_C5.json `
  --instance data/instances/2019-03-20_N20_C5.json `
  --out-dir "$Batch\snapshots" --count 6 --limit 60 --seed 0
```

B. 对上述固定 6 个任务分别进行 bSB、SA、随机样本加相同修复、Exact 本地重放，每任务每方法 3 次，共 72 个逐次 JSON。采样上限 10，返回列上限 3；种子是 `0 + repeat_index`，同一重复的各方法共享种子。

```powershell
& $Python -m run.pricing_compare replay `
  --task-manifest "$Batch\snapshots\fixed_tasks.json" `
  --out-dir "$Batch\classical" --methods bsb sa random exact `
  --require-tasks 6 --task-limit 6 --repeats 3 `
  --sample-limit 10 --max-columns 3 --n-iter 200 --time-limit 60 --seed 0
```

C. **只在以后明确要消耗 CIM 额度时手动执行。本轮未执行此命令。** 在当前 PowerShell 会话先设置 `ECLOUD_ACCESS_KEY` 和 `ECLOUD_SECRET_KEY`，不要把密钥写进命令文件或 Git。SDK 须支持本项目 `cg/pricing/cim_worker.py` 检查的 eCloud `CIMOptimizer` 接口。

此命令冻结 B 的同一批 6 个任务，每任务 3 次，预计 **18 次新请求，上限 18 次**。每个逐次运行最多提交一次，不自动重试；尺寸拒绝、配置失败或超时不会另发补偿请求。超时可能已经消耗一个请求，须检查 `new_request_count`、请求目录及云端状态，禁止直接重跑整个 C 批次。CIM 默认模式是缓存，只有同时指定 `--cim-mode new --allow-new-cim` 才能新提交。

根据现有缓存中 236–489 顶点的 59 次成功请求，云调用最短 66 秒、中位数约 137 秒、75 分位约 261 秒。此前示例里的每次 60 秒限时过短，现将 C 改为每次 600 秒。18 次串行请求粗估约 **45–90 分钟**，队列拥堵时可能接近 **2–3 小时**；600 秒限时给出的理论上界约 3 小时，再加本地建模、修复及写盘时间。历史计时不能保证当前云端速度，也不能保证每次都会成功。

```powershell
& $Python -m run.pricing_compare replay `
  --task-manifest "$Batch\classical\fixed_tasks.json" `
  --out-dir "$Batch\cim_new" --methods cim `
  --require-tasks 6 --task-limit 6 --repeats 3 `
  --sample-limit 10 --max-columns 3 --n-iter 200 --time-limit 600 --seed 0 `
  --cim-mode new --allow-new-cim --cache-dir "$Batch\cim_requests"
```

D. 汇总经典和 CIM 逐次结果，包括失败、空输出及超时。只跑了 B 时，删掉第二个 `--runs` 参数即可。

```powershell
& $Python -m run.pricing_compare summarize `
  --runs "$Batch\classical" --runs "$Batch\cim_new" `
  --out-dir "$Batch\comparison"
```

每个重放目录及汇总目录都生成 `runs.csv`、`task_method_summary.csv`、`summary.json`。逐次 JSON 记录原始输出、每个样本的合法性／冲突／约化成本、修复后的集合与修改数、实际返回列、编码／采样／修复／指标评估／完整墙钟时间。修复计时仅包围原生产修复函数；指标合法性／签名／约化成本评估另记 `evaluation_seconds`。`fixed_tasks.json` 固定任务路径、任务哈希及文件 SHA256；重放前重新验证，防止后续更换任务。

`wall_seconds` 使用真实墙钟，覆盖快照加载、编码、后端调用、修复、指标评估和请求元数据读取，包含 CIM 排队／网络等待；外层 JSON／CSV 写盘不计入。CIM 的 `sampling_seconds` 覆盖整个 worker；其中的 SDK 建模和设备调用另记为 `device_encoding_seconds`、`device_call_seconds`，这些分项不能再与 worker 总耗时相加。

## 定义与实现

快照在主问题产生原始对偶、定价目标更新后、启发式采样前保存。图包含原始顶点、活动顶点、分区、原始／辅助冲突边、合并映射和有效分支约束；保存 Phase I/II、原始对偶、权重、常数、原有列签名、QUBO／Ising 矩阵、归一化与罚值、种子及源码版本。加载时只需要 JSON，不依赖原主问题或 Gurobi 内存对象；Exact 在重放时另建原约束模型。

默认无 `PRICING_SNAPSHOT_DIR`，快照功能关闭。任务哈希覆盖图／有效约束、对偶／常数、阶段、列池、编码和影响编码或有效列阈值的配置（罚值、归一化、epsilon）。阶段或列池改变属于不同任务；相同任务的重复采集写入 `capture_events.jsonl`，不增加快照数。时间戳、节点号、采样种子与迭代／样本预算不参与任务身份。采集命令显式保存根节点号、深度和算例来源。

所有候选集合均从原始对偶重新计算约化成本，低 QUBO 能量不代表有效新列。合法性检查同时检查冲突、被禁止顶点、分区重复以及合并映射。负约化成本阈值沿用快照的 epsilon，已有列按同一签名排除。采样方法全部调用生产代码 `QAIAPricingSolver._repair_independent_set`；随机对照直接复用 `provider="greedy"` 的样本生成路径。

SA 仅依赖 NumPy：每条独立链每 sweep 随机排列顶点并提出单自旋 Metropolis 更新，采用几何温度 `2.0 → 0.01`。默认 200 sweeps，总提议预算是 `200 × 顶点数 × 10`；记录实际完成 sweeps、提议数、种子和超时。bSB 调用本项目已有实现，记录迭代预算、dt、实际 xi、实际 J/h dtype 与矩阵。`cpu-float32` 是历史后端标签；应以记录的实际 dtype 为准。

Exact 解原始约束定价，记录 Gurobi 状态、可行解约化成本、最优约化成本（仅证明最优时提供）、有效约化成本下界及最大权重上界。Exact 结果用于目标质量参考；不能把求解池列数当成随机采样产率。

CIM 请求记录实际设备矩阵、量化矩阵、精度／设备信息及与经典输入的差异；完整设备输出保存为 `device_output_spins.npy`，在 PrecisionReducer 后处理和能量排序之前截取前 10 个。解码输出另存 `raw_spins.npy`，再调用共同修复；SDK 后处理丢弃样本时，设备接收数与解码数分别记录。经典方法保存未量化输入。旧缓存缺少设备量化矩阵时明确记为无法恢复，不能声称其与经典输入相同。CIM 的命令种子仅作为请求与对照标识；当前 SDK 未提供可控制的硬件采样种子，记录其限制，不能声称三种采样器的随机源完全相同。

## 指标分母与重复

`received_sample_count` 是后端输出总数；`raw_sample_count` 是经共同上限截取后实际评估的样本数。逐次比例都保存 `numerator`、`denominator`、`value`；零分母的比例为 null。汇总比例使用跨运行分子／分母之和，并保留二者，包含失败与空输出的零计数。

| 比例 | 分母 |
|---|---|
| 原始合法率、原始唯一率 | 实际评估原始样本数 |
| 修复后唯一合法产率 | 实际评估原始样本数 |
| 唯一负约化成本比例 | 修复后唯一合法集合数 |
| 有效新列占负成本集合比例 | 唯一负约化成本集合数 |
| 修复前／后有效新列产率 | 实际评估原始样本数 |

比较 `raw_effective_new_column_count` 与 `effective_new_column_count` 可观察相同采样批次的修复贡献；比较不同方法相同任务、相同预算下的这两列与最佳合法约化成本可观察采样贡献。汇总计数平均值的分母是全部逐次运行数；最佳约化成本均值只对存在合法值的运行计算，明确记录 `observed_runs`，失败状态单独保留。

请求计数区分 `backend_request_attempt_count`（后端尝试）和 `actual_cloud_submission_count`（已记录的 SDK 创建任务调用次数，不能据此保证云端已接受或扣费）。进程中断或 SDK 无记录时，提交次数可能为 null，不能视为 0。汇总输出各计数的 `known_sum`、`observed_runs` 与 `unknown_runs`；存在未知值时，`known_sum` 只是已证实调用次数／下界。按任务、方法、`sample_source` 分组，保持新请求和缓存对照分开；`independent_repeat_count` 只计去重后的非空样本批次身份，`independent_attempt_count` 保留独立尝试数。

缓存重放保存 `sample_source="cached_cloud"`、样本文件／内容身份与 `independent_repeat=false`。同一缓存重复读三次仍只有一批原始样本；`unique_raw_batch_count` 用于核查，不作为三次新真机重复。可以用 `--methods cim --cim-mode cache --cache-dir results/cim_tasks` 检查现有匹配缓存；此命令不提交新请求。旧缓存若先按能量排序且输出超过共同样本上限，必须能恢复设备原始顺序，否则该运行保留为错误；不能让 CIM 隐含利用更多原始样本择优。

旧 `request.json` 可恢复设备请求顶点 ID、权重、冲突边、禁用顶点和罚值；`samples.npy` 可恢复二进制采样；`cloud_timing.json` 提供云调用时间。它们通常缺少原始对偶、阶段及既有列池，不能单独称为完整可重放定价任务。只有其编码与一个新完整快照精确匹配，才允许绑定到该快照做缓存样本对照；缺少量化信息继续保留缺失标记。

## 本轮已执行的本地验证

实际结果位于 `results/pricing_comparison_local_20261002`。采集 `snapshots_user` 的 6 个根节点快照耗时 22.771 秒；最终 `classical_verified` 完成 72 次本地重放，54 个采样运行完成，18 个 Exact 均最优。另有 `cim_cache_audit` 的 6 个缓存尝试没有找到与这些快照编码精确匹配的旧样本，全部保留为错误；没有新 CIM 请求，因此本轮不能给出 CIM 的质量排名。

三个采样方法的修复前有效新列总数均为 0，修复后逐次有效新列计数之和为 bSB 16、SA 123、随机对照 118。每方法分母是 18 次运行、180 个原始样本；该和会重复计入不同运行中得到的同一列，不是全局唯一列数。结果支持经典修复在这批任务中的贡献，但这 6 个根节点任务不足以推断一般性的采样器优劣。完整检查、Exact 参考值和限制见 `results/pricing_comparison_local_20261002/VALIDATION.md`，最终统一 CSV 为 `comparison_all/runs.csv`。
