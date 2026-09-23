# 9 月 30 日前的 Exact、QAIA、CIM 实验

适用仓库：`Liang023/BP-QAIA-PCP`，核对 GitHub 最新提交 `775ce307`（2026-09-23）。配套文件：`config/cim_only.json`、更新的 `experiments/summarize_scale.py`。保留原目录的运行记录；以下新实验写入全新目录。

## 1. 已上传结果及其含义

| 来源                                                   | 已完成的观察                                                                                                                                                                            | 实验决策                                                                                         |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `results/final_validation_300_v1`                    | 当前 GitHub 只有`2019-03-11_N16_C4` 的部分结果：compact 0.27 秒证明最优值 62；Exact、默认 QAIA、调优 QAIA、Greedy 的已上传 BP 运行均触及 300 秒；最佳排程有 62 或 63，均已验证        | 不把该目录当完成的 30 实例实验；不要运行依赖完整批次的`summarize_scale` 或 `compare_anytime` |
| `results/final_cim_pilot_v1`，`2019-03-05_N12_C3`  | compact 最优值 67。Exact 三次约 5.18–5.29 秒；调优 QAIA 三次约 0.48–0.82 秒；CIM 三次约 183.8–301.7 秒，均返回 67 且证明最优。CIM 每次有 1 次完成的远端请求和 1 次本地超时的第二请求 | CIM 已真实接入，并返回有效列；目前该例上 CIM 明显较慢。正式实验每次 BP 限制为 1 次 CIM 请求      |
| `results/final_validation_v1`，`2019-03-05_N12_C3` | 所有组均证明 67，说明该开发日期适合检查程序流程                                                                                                                                         | 该日期已用于开发，不能重复当作独立测试日期                                                       |

注意新上传的 `final_validation_300_v1/manifest.json` 写明 `EXACT_POOL_SEARCH_MODE=2`、`BPC_PRIMAL_COMPLETION=0`，而调参记录中的 `EXACT_POOL_SEARCH_MODE=0`。正式实验应固定统一环境，并在新目录从头运行各组；已上传的部分验证结果单独报告，不与新参数条件直接合并。

## 2. 保留哪些比较方法

主对照为纯 Exact 定价 BP；实验方法为调优后的 QAIA+Exact 与真实 CIM+Exact。三者共享主问题、可行性验证、停止预算和 Exact 最终定价认证。Compact MILP 每实例运行一次，用于取得已证明的最优值，是必要的参照，运行开销通常很小。删去 Greedy 和未调参的 QAIA 可以节省运行时间；相应地，论文/比赛报告只能声称与 Exact 对照的表现，不能据此声称优于一般启发式。

`config/cim_only.json` 恰好只有一个 `cim` 变体；`--qaia-config` 自动追加 `qaia_tuned`。**不要再加 `--include-cim`**，否则变体重名。这里的一组 Exact 只跑精确定价；它在 300 秒内若仍未证明最优，已验证的排程依然是有效结果。

## 3. 固定十二个正式实验实例

从 GitHub 已上传的原始 ACN 会话 `data/raw/acn/caltech_march_holdout.json`，按现有 `experiments.prepare_scale` 生成 03-11、03-12、03-13、03-14 四天的 N8/C2、N12/C3、N16/C4：**4 个日期 × 3 个规模 = 12 个实例**。四天连续、每一天采用同一规模设计，不根据算法胜负挑选。N16/C4 的 03-11 已见 BP 难以证明最优，保留它检验限时性能；N8 和 N12 用于争取报告已证明最优的实例。**规模小不保证 BP 必然 optimal**，应以正式运行状态为准。

在项目根目录的 Windows PowerShell 中运行；输出目录必须此前不存在：

```powershell
python -m experiments.prepare_scale --family acn --raw data/raw/acn/caltech_march_holdout.json --dates 2019-03-11 2019-03-12 2019-03-13 2019-03-14 --sizes 8 12 16 --ratios 4 --slot-minutes 15 --power-kw 7 --out-dir data/acn_competition_0930_v2
```

生成文件 `data/acn_competition_0930_v2/instances.json` 包含十二个实例和绝对路径。在生成和批量求解之间不要移动项目文件夹。N8/C2 中 N 表示 8 辆车，C 表示 2 个充电桩；N12/C3、N16/C4 同理。`ratios 4` 表示每 4 辆车配置 1 个桩。四个日期均在离线调参训练日期 03-04、06、08 之外。所有新实例保持原转换器的 15 分钟和 7 kW 假设。

## 4. 固定正式实验环境

以下环境值在三组批次启动前一次性设置；调参仍在单独的离线过程进行，其耗时不计入 BP 时间。你之前上传的 CIM 任务名修复已在 GitHub：`bp` 加 20 位 UUID，满足平台 5–24 字符限制，无需再次修改它。

```powershell
$env:EXACT_POOL_SEARCH_MODE = "0"
$env:BPC_COMPLETION_ROWS = "vehicle"
$env:BPC_RMP_MIP = "1"
$env:BPC_RMP_MIP_EVERY = "20"
$env:BPC_RMP_MIP_SECONDS = "0.5"
$env:BPC_RMP_MIP_FRACTION = "0.1"
$env:BPC_PRIMAL_COMPLETION = "0"
$env:CIM_DEVICE_ID = "WuYue-QPU-Qboson-1000"
$env:CIM_MAX_BITS = "1000"
$env:CIM_PRECISION = "8"
$env:CIM_MAX_CALLS = "1"
$env:CIM_CALL_SECONDS = "90"
$env:ECLOUD_ACCESS_KEY = "你的访问密钥"
$env:ECLOUD_SECRET_KEY = "你的秘密密钥"
```

下面直接执行正式批次，不安排烟雾测试或单实例预检。批次中的 CIM 运行会提交真实云端任务。之前首个 CIM 请求约 63–68 秒完成，因此每次求解最多提交一次、等待上限设为 90 秒。正式结果检查 `statistics.root_diagnostics.heuristic_metrics.cim` 中的 `completed` 与 `returned_columns`：若任务超时或没有返回有效改进列，就如实报告，不能把该运行算作 CIM 成功提供列。本地超时后的远端任务可能继续执行。

## 5. 正式三组批次及输出

每实例用 3 个固定种子做 QAIA 与 CIM 重复；Exact 也重复 3 次观察运行时间波动，虽然 `BPC_PRIMAL_COMPLETION=0` 时它的随机种子均为 0。十二实例包括三种规模和四个独立日期，比原来的六实例覆盖更充分；三次重复仍不宜用于宣称稳定的统计优势。此次比赛先完整报告十二实例的全部运行，论文后续可按同一设计增加日期和种子。

```powershell
python -m experiments.run_batch --instance-list data/acn_competition_0930_v2/instances.json --variant-file config/cim_only.json --qaia-config tuning/acn_train_v1/best_qaia.json --seeds 0 1 2 --exact-repeats 3 --limit 600 --out-dir results/competition_three_600_v2
python -m experiments.summarize_scale --results-dir results/competition_three_600_v2 --out-dir results/competition_three_600_summary_v2
python -m experiments.compare_anytime --results-dir results/competition_three_600_v2 --checkpoints 120 300 600 --out-dir results/competition_three_600_report_v2
```

`summarize_scale` 只有在十二实例全部结束后才能执行；中途看每个实例的 `*_diagnostic.json`。当前 `run_batch` 没有自动续跑，旧 `results/final_validation_300_v1` 不应直接继续用于这套新设计。三个输出目录每次运行必须新建。

## 6. gap 是什么，现在怎样得到

原 BP JSON 的 `statistics.global_lower_bound` 和 `statistics.gap` **已经存在**，但原 `summarize_scale` 没导出到逐次实验 CSV。当前 BP 在限时终止时采用安全但较松的解析下界；03-11 N16/C4 的 Exact 最好值 62、BP 下界 53，因此 BP 自报 gap 约 14.52%，即使 compact 已证明真正最优也是 62。不可把这个 14.52% 理解为排程距已知最优值的误差。

替换后的 `experiments/summarize_scale.py` 在 `runs.csv` 增加：

| 字段                      | 算法与解释                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `bp_lower_bound`        | BP 输出的解析下界                                                                                                              |
| `bp_gap_percent`        | `100 × (已验证可行目标值 − BP下界) / 已验证可行目标值`；是可证的上界 gap，可能很松                                         |
| `reference_gap_percent` | 当 compact 已经证明最优时，`100 × (已验证可行目标值 − compact最优值) / 已验证可行目标值`；直接表示当前排程与已知最优的差距 |
| `deviation_percent`     | 原字段，`100 × (可行目标值 − compact最优值) / compact最优值`，分母与上一个字段不同                                         |

`summary.csv` 也有两种 gap 的每组条件中位数。所有 gap 只为已经验证的可行排程计算；无可行解保留空值。`reference_gap_percent=0` 且 `status=time_limit` 表示 **找到最优目标值但 BP 尚未完成最优性证明**；`status=optimal` 才表示 BP 自身证明。报告中分别统计各方法的可行率、达到已知最优值的次数、BP 自证次数、时间和 gap。Compact 必须已证明且排程通过验证，才能使用参考 gap。

## 7. 时间和请求量估算

这套命令是串行运行，每实例 `1 compact + 3 Exact + 3 QAIA + 3 CIM = 10` 次；十二实例共 **120 次运行**，其中 108 次为 BP，真机请求最多 **36 次**（`CIM_MAX_CALLS=1`）。若 108 次 BP 全部用满 300 秒，BP 时间为 **9 小时**，再加 12 次 compact、进程启动和文件开销，可按 **约 10 小时** 留机器运行窗口；外层保护上限 `300+60` 秒给出的机械上界为 108 × 360 秒，即 **10 小时 48 分**，再加 compact 与其他开销。已上传的 N12/C3 CIM 实测约 184–302 秒，是最多三次请求的结果；本次限制一次后，实际时间仍以新实例运行情况为准。

十二实例和三次重复构成这次完整的正式批次。如果 BP 在 N16/C4 上仍多为限时，可以同时报告这些运行到达已知最优目标值的次数；若重点一定是 **BP 证明 optimal 的时间**，只在同一批结果中分析已证明的实例及其时间，不能把 compact 的证明时间算成 BP 的证明时间，也不能用事后删掉较难实例的方式提高证明率。

## 8. 报告中的结论边界

`paired_summary.csv` 比较相同实例/重复编号下三种方法的 30、120、300 秒最好可行解；CIM 的种子只控制本地流程，云端 CIM 未承诺可用该种子复现实物采样。真机等待应计入 300 秒在线预算。若小规模运行多为 optimal，就比较证明时间；若 N16/C4 多为 time_limit，就比较可行率、达到已知最优的时间与 gap。当前已上传数据能证明 CIM 被真实调用并返回列，尚不能证明 CIM 比 Exact 或 QAIA 更快、更优。
