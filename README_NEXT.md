# BP 现阶段改动：把采样列转为可行排程

适用仓库：Liang023/BP-QAIA-PCP，基于 `d4c30ad00ace244801024e315d4a6e3db382a7dc`。
本目录内四个 .py 文件按相同相对路径覆盖仓库文件；README 是操作说明，不覆盖仓库现有 README。

## 先看已有结果

依据 `results/cim_active_20260923_184108_summary/summary.csv` 和 `comparisons.csv`：

| 方案          | 限时可行 | 证明最优 | 当前可解释的结果                                                          |
| ------------- | -------: | -------: | ------------------------------------------------------------------------- |
| Exact-BP      |    12/12 |     7/12 | 单次确定性运行，各实例的主要 BP 基线                                      |
| QAIA+Exact-BP |    36/36 |    16/36 | 03-13 N20/C5 的三个种子目标 67、67、66，Exact 为 70；在另外一些实例更差   |
| CIM+Exact-BP  |    27/36 |     8/36 | 9 次 cloud worker 失败集中在三个实例；不能把失败批次解释成 CIM 的排程优势 |
| compact MILP  |    12/12 |    12/12 | 每实例一次，约 0.05–0.26 秒；继续保留为已知最优值参照                    |

这里 QAIA/CIM 有 3 个种子，Exact 只有 1 次；“证明最优”和“找到与参照相同的目标”是两回事。
不要把 36 次随机运行当成 36 个独立实例，或用不同日期中仅 QAIA 获胜的算例事后选测试集。
从现有结果不能声称 QAIA 或 CIM 已经稳定优于 Exact。

## 为什么动这些代码

上一份图着色混合 BP 论文强调多样候选列、Exact 收尾认证和利用现有列产生可行整数解；
Maher 与 Rönnberg (2023) 指出 LP 定价列未必适合拼接整数解，主张移除部分现有整数列并做修复。
你的根节点已经有一个未开启的补全器：它只从 LP 列留下一部分，而且不允许把剩余车辆加入已经保留的桩列。
此前 `run/run.py` 将 `BPC_PRIMAL_COMPLETION` 固定为 `0`，所以这一步没有进入正式比较。
与此同时，CIM 云端 worker 一旦失败，原实现直接终止整次 BP，导致 9 次 error。

这轮只做有限的原始侧改动，不改变定价目标、模型约束、节点下界、CIM 排队计时或事先固定的 QAIA 参数：

| 文件                                        | 改动                                                                                                                                                                                                           |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cg/primal_completion.py`                 | 交替使用当前 incumbent 和根节点 LP 列作为部分解；先移除较晚结束的 incumbent 桩列，再给缺失车辆分配候选区间；允许向已有桩列继续追加不冲突车辆；仅将完整排程所用列放入池。候选结束时间必须严格小于当前最好目标。 |
| `bpc/branch_and_price.py`                 | 把已验证的 incumbent 和当前上界传给根节点修复；统计调用、生成列、完整排程、上界改善及是否以 incumbent 为种子。候选仍须通过现有`validate_schedule` 才能更新上界。                                             |
| `cg/pricing/qaia_exact_pricing_solver.py` | CIM worker 返回 RuntimeError / ValueError 时，记录`heuristic_failures` 并运行已有 Exact 定价；QAIA 错误仍显式报错，Exact 超时仍不宣称已认证。CIM 调用失败保留在原 CIM task metrics 内。                      |
| `run/run.py`                              | 默认启用同一根节点修复（Exact / QAIA / CIM 都启用），20 次尝试、最多 2 秒；新增 `--primal-completion 0                                                                                                         |

这是一个上界启发式，不是 Maher–Rönnberg 完整的 IPColGen；没有实现新的修复定价子问题，也没有增加云端调用。
当根节点没有完成精确定价认证时，本版本暂不运行根节点修复；已有的 RMP 整数解与 restricted MIP 路径仍正常记录。

## 怎样调用（Windows PowerShell）

把四个 .py 文件覆盖至仓库同名路径，在仓库根目录执行：

```powershell
python -m run.run --out-dir results/primal_repair_v2 --limit 600 --seeds 0 1 2 --exact-repeats 3
```

程序沿用现有 12 个实例；每个实例 compact 跑一次作最优值参照，Exact、QAIA、CIM 各跑三个种子。
生成 `results.csv`、旁边的 `_summary` 和 `_anytime` 目录；统计信息里 `primal_completion`
包含补全指标，CIM 的 `root_diagnostics.heuristic_metrics.heuristic_failures` 指示云端失败回退次数。
CIM worker 失败后若 Exact 接管成功，该次结果应解释为“CIM 调用失败、Exact 回退”，不能算 CIM 的成功。
按 600 秒上限，仅 12 × (3+3+3) 次 BP 的活跃时间上界就是 18 小时，
另有 compact、汇总及 CIM 云端排队的真实时间；通常会提前完成一部分，但不能承诺实耗。

如果要核查本次改变是否带来收益，使用另一个输出目录、同一实例/种子/预算：

```powershell
python -m run.run --out-dir results/primal_repair_off --limit 600 --seeds 0 1 2 --exact-repeats 3 --primal-completion 0
```

检查各实例每种子目标、可行率、达到已知最优值的次数，以及 `_anytime` 的首次可行时间和最好值轨迹。
额外 2 秒是单次根节点修复上限，记入 BP 活跃时间；两种设置都保留 compact 单次参照。
因改了代码和随机性，不要用旧批次直接替代这组同代码消融，也不能将 CIM 云端排队排除后的 600 秒称作现实经过的 600 秒。

## 何时继续做更复杂的“整数定价”

先看修复产生的 `complete_schedules` 与 `improvements`，以及 QAIA/CIM 是否在相同条件下增加获胜实例。
若修复能改善上界，再考虑 Maher–Rönnberg 式按车辆覆盖缺口生成专用修复列，并单独保留标准 Exact 定价用于认证；
若只是增加列而不能改善上界，继续加 QAIA/CIM 迭代或云端调用没有实验依据。

参考：

- Vercellino 等，*Hybrid Quantum-Classical Branch-and-Price Method for the Vertex Coloring Problem*, arXiv:2508.18887.
- Maher 与 Rönnberg，*Integer programming column generation*, Mathematical Programming Computation 15 (2023), 509–548, DOI:10.1007/s12532-023-00240-w.
