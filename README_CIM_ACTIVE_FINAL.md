# 真实 CIM 无本地等待上限、暂停 BP 计时与正式实例方案

本版基于 `Liang023/BP-QAIA-PCP` 提交 `8d353cb2e0ada608b599813ec4a69382951e2b2a`（2026-09-23）。替代上一版缓存重放补丁。直接使用真实 Kaiwu CIM 调用，SDK 自己管理其缓存；本版没有新增缓存匹配、缓存重放或预先求解。

## 1. 原代码哪里有问题，本版怎么改

原先 `cg/pricing/cim_backend.py` 把 CIM 子进程的超时时间设为 `min(CIM_CALL_SECONDS, BP 剩余时间)`。即使解除它，`experiments/run_batch.py` 还有 `timeout=limit+60`，会在云端排队期间终止整个求解进程。BP、列生成、可行解轨迹也各自读取墙钟，所以只在最终结果中减去排队时间不能修复超时和检查点。

本版使用同一套 BP 计时：

`BP 求解时间 = 从建图开始的实际耗时 − 已测量的阻塞云调用耗时`

- Worker 在 `PrecisionReducer.solve(submitted)` 前后测量云调用时间；建模、子进程启动、结果解码、修复、后续 Exact 和主问题计算均计入 BP 时间。
- CIM 父进程等待 Worker 返回，不设置本地超时；返回后将该云调用时间从 BP 时钟中扣除，然后继续原有列验证和定价流程。
- 外层批次对 `cim_root` 使用 `timeout=None`，不会因为排队超过 600/660 秒杀掉求解进程。
- BP 的截止时间、Gurobi 剩余限时、节点计时、定价计时、首次可行解时间、10/30/120/600 秒检查点均使用同一 BP 时钟。
- `wall_seconds` 仍记录真实等待总时长，单独输出。它不控制 CIM 的 BP 限时。

**时间名称要准确：当前 SDK 调用没有提供纯排队与设备执行的分段时间。本版扣除的是整个阻塞 SDK 调用区间，其中包含上传、排队、云端计算、返回和该调用内部的 SDK 工作，字段名为 `cloud_excluded_seconds`。不能把它写成已精确测得的“纯排队时间”。**

例如真实排队调用用了 500 秒、本地建模和 BP 共用了 8 秒，结果中 `wall_seconds≈508`、`cloud_excluded_seconds≈500`、`solve_seconds≈8`。解进入 BP 时间的 10 秒检查点，同时轨迹保留约 508 秒的实际获得时间。论文可表述为“以扣除阻塞云调用时间后的 BP 计算时间为预算，并单独报告端到端耗时”。这不是端到端 10 秒返回结果的结论。

## 2. 等待返回与成功的含义

已移除 `--cim-call-seconds` 与 `CIM_CALL_SECONDS` 的使用。云任务等待期间本地程序可以持续运行，SDK 返回后检查存在非空二维 0/1 样本，再继续 BP。旧命令不要再附加 `--cim-call-seconds`。

等待没有本地时限；服务故障、认证失败、SDK 报错仍会形成明确的错误结果，不能保证第三方平台永不失败。返回的样本不一定包含新的负约化成本列；没有改进列时继续 Exact 定价是原有算法逻辑。

`CIM_MAX_CALLS=1` 继续表示每次求解的 CIM 调用次数上限，不是等待秒数。此设置控制云任务数量。结果中检查 `cim_requests`、`cim_completed` 和 `heuristic_returned_columns`，分别表示提交次数、成功返回次数和产生的列数。

## 3. 逐文件修改清单

| 文件 | 改动及原因 |
| --- | --- |
| `cg/budget_clock.py`（新增） | 提供所有 BP 组件共用的计时，以及累计扣除的云调用秒数。 |
| `cg/pricing/cim_worker.py` | 在实际 SDK `solve` 调用处测时并写入 `cloud_timing.json`；返回或抛错均记录。继续使用现有 SDK 缓存。 |
| `cg/pricing/cim_backend.py` | 取消 Worker 本地超时，读取云调用秒数调整 BP 时钟，要求非空有效样本，平台失败直接记录错误；删除本地等待秒数配置。 |
| `cg/deadline.py` | 所有剩余时间计算改用 BP 时钟。 |
| `bpc/branch_and_price.py` | 总求解时间、分支、节点、初始列、受限整数主问题的计时与截止检查统一。 |
| `cg/column_generation.py` | 列生成截止检查、主问题和定价耗时统一。 |
| `cg/pricing/qaia_exact_pricing_solver.py` | 启发式和 Exact 的局部计时统一，避免把云等待计入定价总时长。 |
| `cg/master/restricted_integer_master.py` | 受限整数主问题的剩余限时与回调截止检查统一。 |
| `cg/makespan_bounds.py` | 下界计算使用同一时钟，数学下界公式不变。 |
| `cg/primal_completion.py` | 可行解补全组件的截止检查统一。 |
| `cg/anytime.py` | incumbent 使用 BP 时间；每次更新额外记录真实墙钟和累计排除的云时间。 |
| `experiments/run_instance.py` | 每次求解重置时钟，输出 `solve_seconds` / `wall_seconds` / `cloud_excluded_seconds`，超预算量按 BP 时间计算。 |
| `experiments/run_batch.py` | 取消 CIM 外层进程超时，保存新计时口径；汇总求解时间使用 `solve_seconds`。 |
| `experiments/summarize_scale.py` | 最终 CSV 与轨迹 CSV 输出双时间和 `timing_basis`。 |
| `experiments/compare_anytime.py` | 标明检查点计时口径；Exact 只跑一次时，三个启发式重复都与同一 Exact 基线比较，不遗漏 s1/s2。 |
| `run/run.py` | 默认使用下述 12 实例，BP 限时 600 秒，QAIA/CIM 三次、Exact 一次；支持 `--exact-repeats`；取消云等待秒数参数，加入 10 秒报告。 |
| `tests/test_cim_budget_clock.py`（新增） | 不连接云端，验证长等待扣除、多个调用累计、检查点和本地超时。 |
| `tests/test_final_workflow.py` | 将旧“超时返回空样本”预期改为无等待上限，并补齐模拟 Worker 时间记录。 |
| `data/acn_scale_final_v3/`（新增） | 12 个实例、12 份转换审计和可移植相对路径 manifest。 |

不能只替换 `cim_backend.py`：其他组件若仍使用旧墙钟，云结果返回后仍可能立即判断超时。因此请按压缩包目录完整覆盖这次修改文件。

## 4. 新算例：同一 N 只对应一个 C

采用 2019-03-11、2019-03-12、2019-03-13 三个日期，每个日期四个规模，共 12 个实例：

| 规模 | 车辆数 N | 桩数 C | 03-11 顶点数 | 03-12 顶点数 | 03-13 顶点数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| N8/C2 | 8 | 2 | 199 | 181 | 174 |
| N12/C3 | 12 | 3 | 281 | 305 | 250 |
| N16/C4 | 16 | 4 | 372 | 405 | 371 |
| N20/C5 | 20 | 5 | 470 | 489 | 475 |

N/C 始终为 4，避免同一车辆集反复改变 C 形成容量敏感性网格。保留 N8/C2 作为已经有最优性结果的小规模参照，增加 N20/C5 扩展规模；由原来的 4 日期×3规模改为3日期×4规模。原始编码顶点数加辅助位低于1000；实际精度处理仍由SDK完成。

使用原仓库 `data/raw/acn/caltech_march_holdout.json`、原 `ev/acn_to_ev.py` 与 `experiments/prepare_scale.py` 生成。规则继续为：按当地到达日分组，以到达时间和 session ID 排序取前 N 条合格会话；同一日期的大 N 包含小 N 会话；15 分钟时间槽、7 kW 同质桩、保留全部可行开始时刻。处理能量无效、时间窗口不足、重复记录等情况仍由原转换器写审计。

固定 N/C 只控制车辆/桩比例，不保证不同日期有相同能源负荷，也不保证难度随 N 单调递增。没有根据算法胜负、gap 或是否最优来删选实例。N20 是否能在600秒BP预算内证最优，需由正式结果回答。

压缩包已附生成好的实例，可直接运行。如需从同一原始数据重建到**新目录**：

```powershell
python -m experiments.prepare_scale --family acn --sizes 8 12 16 20 --ratios 4 --dates 2019-03-11 2019-03-12 2019-03-13 --raw data/raw/acn/caltech_march_holdout.json --max-vertices 999 --slot-minutes 15 --power-kw 7 --out-dir data/acn_scale_rebuilt
```

## 5. 直接进行正式实验

1. 将包内目录覆盖至仓库根目录。`run/run.py` 仍在文件顶部放密钥；交付文件为占位符，把你原有的两项值保留进去即可。
2. 不要把本次代码替换到正在运行的旧批次中。使用新结果目录，旧结果保留。
3. 在仓库根目录的 PowerShell 执行：

```powershell
python -m run.run --out-dir results/final_active_600_v3
```

也可以直接在编辑器运行 `run/run.py`；会自动创建带时间戳的新输出目录。默认跑全部12实例，没有额外的试运行阶段。无需设置 PowerShell 环境变量。

默认是：compact 每实例1次、Exact 1次、QAIA 3次、CIM 3次，共96次运行。Exact 使用固定求解器种子、单线程、关闭随机 primal completion，因此为减少重复计算默认一次；如需测运行时间波动，可追加 `--exact-repeats 3`。CIM 的 s0/s1/s2 是本地重复编号，现有 SDK 接口没有传入可控设备 seed；若SDK复用缓存，不应把三次相同硬件样本解释为三次独立设备随机采样。

完成后总表：`results/final_active_600_v3/results.csv`。检查点：`results/final_active_600_v3_anytime/checkpoints.csv`。每次运行的 JSON、log 和 incumbent 轨迹也会保留。

关键列：

| 字段 | 含义 |
| --- | --- |
| `solve_seconds` | 论文所定义的 BP 计算时间；600 秒限制作用于它 |
| `wall_seconds` | 同一起点开始的实际耗时，包含云调用 |
| `cloud_excluded_seconds` | 实测并扣除的 SDK 云调用总时间 |
| `first_feasible_seconds` / `best_found_seconds` | BP 时间口径下的首次/最好解时间 |
| 轨迹的 `wall_seconds` | 该次可行解在真实时间轴上何时出现 |
| `cim_seconds` / `cim_local_seconds` | CIM Worker 整体耗时 / 扣除云调用后的本地部分 |
| `timing_basis` | 本版为 `bp_active_excluding_cloud_call`，旧结果缺省为 `wall` |
| `bp_lower_bound` / `bp_gap_percent` | 本算法的有效下界和 gap |

## 6. 总运行时间怎样估计

若所有运行都用满600秒，12×(1 compact+1 Exact+3 QAIA+3 CIM)×600≈**16小时计算预算**，加上进程启动和报告时间。CIM 至多36次调用：若平均每次云调用4分钟，额外约2.4小时；10分钟则额外约6小时。提前 optimal 的运行会减少计算时间。

由于云等待已无限制，总墙钟没有固定上界。600秒不是“电脑经过600秒后必定结束”，而是 BP 的计算预算。论文建议同时报告解质量、有效gap、BP时间和云调用耗时，读者才能复现实验口径。

## 7. 本地验证与旧文件处理

本次已进行：Python语法检查；两个不联网的计时测试；两车辆小例的完整 BP 集成验证（模拟500秒云调用，实际时间记录约500秒，BP时间约0.006秒，返回最优可行解并正常进入10秒检查点）。这是代码计时验证，不能作为CIM真机性能结果。没有提交新的真机任务。

原 `tests/` 保留。本版替换了其中旧CIM超时预期，不需要删除整个测试目录。

若安装过上一版重放补丁，可删除 `config/cim_replay.json`、`experiments/inspect_cim_cache.py`、`README_CIM_TIMING_REPLAY.md`；本版不引用它们。旧 `data/acn_capacity_grid_v1/`（同N不同C）不再用于主实验，可归档。旧实验结果的计时口径不同，保留作为历史记录，不与新BP时间检查点直接合并。
