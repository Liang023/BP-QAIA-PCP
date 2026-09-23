# BP–QAIA–CIM 最终实验版

基于 Liang023/BP-QAIA-PCP 的提交 `231fe9c9c744d679ded0c6d121d79e2b4a032ad0`，2026-09-22。

目标：在相同在线总时间预算下，比较 Exact、Greedy+Exact、QAIA+Exact、CIM+Exact 的可行排程质量；Compact MILP 保留为独立基准。本版完成实验接口，不预先宣称 QAIA/CIM 有优势。根节点补全仍然可开关，所有 BP 方法使用同一补全策略。

## 1. 本次修改了什么，为什么

| 文件 | 改动与原因 |
| --- | --- |
| experiments/tune_qaia.py（新增） | 使用 Optuna TPE 离线调节 BSB 的 n_iter、batch_size、dt、xi；评价固定时间 BP 解质量，而不是单次定价速度 |
| config/qaia_runtime.py | 支持 QAIA_XI、冻结配置加载、SHA256 与调参耗时追踪 |
| experiments/run_instance.py | 新增 --qaia-config、greedy_root、cim_root；记录离线调参信息和训练集重叠标志；BP 内不执行调参 |
| experiments/run_batch.py | 新增 --qaia-config、--include-cim；清理继承的 QAIA 环境选项；按真实后端标注方法 |
| cg/pricing/qaia_exact_pricing_solver.py | 将 cim 接入原混合定价，沿用相同冲突修复、真实约化成本检查、去重和 Exact 认证 |
| cg/pricing/cim_backend.py、cim_worker.py（新增） | 采用上传 QBendersOCT.py 的移动云 SDK 接口，限制请求次数、本地等待时间、设备规模；记录任务状态 |
| experiments/check_cim.py（新增） | 检查 SDK 构造接口和 QUBO 转换，不发送任务、不需要云密钥 |
| experiments/inspect_acn_dates.py（新增） | 调用原 ACN 转换器审计日期、有效车辆数和候选顶点数，不运行优化算法 |
| experiments/prepare_scale.py | 透传 --slot-minutes 和 --power-kw，让规模生成与日期审计使用同一处理参数 |
| experiments/summarize_scale.py | 报告 CIM 请求/返回/超时/规模跳过次数，以及冻结参数哈希 |
| config/final_variants.json、acn_final_split.json | 固定正式对照方法和按日期划分的数据计划 |
| tests/test_final_workflow.py | 测试冻结参数、调参评分、CIM 请求预算、QUBO 构造与解码；不调用真机 |

原来的 bpc、primal_completion、主问题和 Exact 数学模型不改。以前的 QAIA 50/4 和 200/10 只是两种手工配置；现在增加自动调参，保留默认 QAIA 作为消融。

## 2. 安装和检查

交付提供完整代码包和仅修改文件的覆盖包。已有项目先备份，使用覆盖包按相对路径替换；完整包适合解压到新目录运行。两者均不包含旧 results，不会自动删除或迁移实验记录。完整包带有仓库已有 data；新增验证/测试日期需要另行下载。

在 Windows PowerShell 的项目根目录执行，使用你现有的 Python 3.10 环境和 Gurobi 许可。

```powershell
python -m pip install -r requirements-final.txt
python -m pytest -q
```

Kaiwu 不在 requirements 中自动安装。使用你运行 QBendersOCT.py 时安装的移动云版 SDK，不要直接用同名 PyPI 包替换。公开 Kaiwu 1.3.1 文档列出的 CIMOptimizer 构造器与上传代码不同；本版适配的是上传代码的 access_key、secret_key、device_id 接口。

## 3. 调参时间和 BP 时间如何区分

调参是单独命令，正式求解是另一个进程。不存在“BP 中途调参，再暂停计时”的做法。

| 指标 | 统计内容 | 是否计入正式 BP wall_seconds |
| --- | --- | --- |
| best_qaia.json 中 tuning_seconds | 本次离线搜索与训练求解总耗时 | 否 |
| offline_tuning | 正式运行引用的调参记录、哈希、训练实例、调参耗时 | 仅元数据，不累加 |
| tuning_seconds_in_bp | 恒为 0 | 无调参工作 |
| wall_seconds | 图转换、模型构造、定价、修复、补全、整数启发式、分支搜索 | 是 |
| CIM 本地请求/等待/解码 | 发生在 BP 搜索期间 | 是 |
| workflow_seconds / process_seconds | 本次程序启动、准备和记录等更宽范围时间 | 另外保留 |

主计时沿用仓库约定：输入检查和依赖预加载之后、图构造之前开始。冻结 JSON 在计时前加载；它不是对当前测试实例重新调参。首次安装、训练阶段和其他实例的调参耗时不加入本次 BP。论文仍应单独报告离线训练代价。

## 4. Optuna 调参方法

参考 MindQuantum 官方示例使用 Optuna 建立 objective、采样参数、优化并保存最优参数。这里把官方 MaxCut 示例中的“最大割值”替换为本项目“限时 BP 可行解质量”，而不是复制其应用目标。

搜索空间：

| 参数 | 范围 |
| --- | --- |
| n_iter | 50、200、500、1000、2000 |
| batch_size | 4、10、20、50 |
| dt | 0.05–1.5 |
| xi_mode | auto 或 tuned |
| xi（tuned 时） | 0.1–2.0 |

BSB、cpu-float32、Ising 归一化、最大返回列数 3、连续启发式上限 3 固定。第一 trial 为原默认 200/10、dt=1、xi=auto。每组参数使用相同训练实例、种子和单次 BP 预算；TPE 的随机种子也记录。CPU 时间波动仍可能影响限时结果，不承诺逐位复现搜索轨迹。

调参评分为：

`缺失可行解的运行次数 + sum(有效目标值 / 对应实例时间范围) / (运行总数 + 1)`。

目标值不会超过输入时间范围，因此缺失一次的惩罚高于所有可行解质量项。这个值只是供 Optuna 排序的损失，不是平均 makespan。原始无解仍保存 objective=null，不用伪造目标值参与结果表。status=error 会中止调参并留下原始日志，不把程序异常当差参数。原始 trial 记录、study.sqlite3、trials.json 全部保留。

先设置统一实验环境：

```powershell
$env:EXACT_POOL_SEARCH_MODE = "0"
$env:BPC_COMPLETION_ROWS = "vehicle"
$env:BPC_RMP_MIP = "1"
$env:BPC_RMP_MIP_SECONDS = "2"
$env:BPC_RMP_MIP_EVERY = "20"
$env:BPC_RMP_MIP_FRACTION = "0.1"
$env:BPC_PRIMAL_COMPLETION = "1"
$env:BPC_PRIMAL_ATTEMPTS = "20"
$env:BPC_PRIMAL_SECONDS = "2"
```

先做两次 trial 的流程测试；其结果不能直接作为论文最终参数：

```powershell
python -m experiments.tune_qaia --instance data/ev_instances_v1/v1_N6_C2_s0.json --trials 2 --seeds 0 --limit 10 --out-dir tuning/smoke_v1
python -m experiments.run_instance --instance data/ev_instances_v1/v1_N6_C2_s0.json --method qaia_root --qaia-config tuning/smoke_v1/best_qaia.json --seed 1 --limit 30 --out results/final_smoke/qaia_tuned.json
```

正式离线调参示例，使用现有开发日期：

```powershell
python -m experiments.tune_qaia --instance data/acn_scale_v4_grid/2019-03-04_N16_C4.json --instance data/acn_scale_v4_grid/2019-03-06_N24_C6.json --instance data/acn_scale_v4_grid/2019-03-08_N24_C6.json --trials 30 --seeds 0 1 2 --limit 120 --out-dir tuning/acn_train_v1
```

该计划共 270 次训练求解，预算上界约 9 小时，加启动开销；可先用 10 trials、2 seeds 筛查流程。正式参数需要在验证日期检查，不能只看训练分数。验证完成后复制/保留 best_qaia.json 即冻结，不在测试集重新运行调参。增大正式预算到 300/600 秒时，应先在验证集观察参数迁移效果。

调参发生中断时 SQLite 与已完成运行仍在；本脚本没有自动续跑同目录功能。使用新输出目录重启，旧结果保留供审计。

## 5. 单实例和批量调用

```powershell
python -m experiments.run_instance --instance data/acn_scale_pilot/2019-03-05_N12_C3.json --method exact --seed 0 --limit 300 --out results/final_single/exact.json
python -m experiments.run_instance --instance data/acn_scale_pilot/2019-03-05_N12_C3.json --method greedy_root --seed 0 --limit 300 --out results/final_single/greedy.json
python -m experiments.run_instance --instance data/acn_scale_pilot/2019-03-05_N12_C3.json --method qaia_root --qaia-config tuning/acn_train_v1/best_qaia.json --seed 0 --limit 300 --out results/final_single/qaia.json
```

greedy_root/cim_root 自动选对应后端；旧 qaia_root 入口仍兼容 QAIA_PROVIDER 环境变量。推荐批量命令，配置会清除继承的 QAIA 参数，避免旧终端参数污染。单实例默认 exact_mode 仍保留原仓库的 always；如要与批量 on_qaia_failure 完全一致，执行 `$env:QAIA_EXACT_MODE = "on_qaia_failure"`。冻结 QAIA 配置会覆盖其记录的 QAIA 参数。

批量不含 CIM：

```powershell
python -m experiments.run_batch --instance data/acn_scale_pilot/2019-03-05_N12_C3.json --variant-file config/final_variants.json --qaia-config tuning/acn_train_v1/best_qaia.json --seeds 0 1 2 3 4 --exact-repeats 5 --limit 300 --out-dir results/final_validation_v1
```

包含 Compact、Exact、默认 QAIA、调优 QAIA、Greedy10。开启补全后 Exact 也带随机性，所以正式用 10 个种子时，设置 --exact-repeats 10。Compact 在每实例每批中执行一次；是否补做计时重复另列说明。

## 6. CIM：与你的 QBendersOCT 一致的调用链

采用同一个最大权独立集 QUBO：`-sum(w_i*x_i) + P*sum(x_u*x_v)`，自环加 `P*x_i`。P 使用原 QAIA 的权重上界规则。使用 `kw.core.Binary`、`kw.qubo.QuboModel`、`qubo_model_to_ising_model` 建模转换，避免混用 MindQuantum 和 Kaiwu 的 Ising 符号约定。

随后调用 `kw.cim.CIMOptimizer(..., wait=True, interval=1, access_key=..., secret_key=..., device_id=...)`，外套 `kw.cim.PrecisionReducer(optimizer, precision, target_bits=max_bits)`；按原始精度矩阵的 Hamiltonian 排序，使用 `kw.core.get_sol_dict` 解码，再走与 QAIA 相同的原图修复和真实约化成本筛选。所有后端只在根节点调用；Exact 负责最终定价认证。

先做不提交任务的检查：

```powershell
python -m experiments.check_cim
```

设置凭据和设备参数；这里不提供、不保存上传附件里的密钥。附件曾包含明文密钥，应在云端更换。

```powershell
$env:ECLOUD_ACCESS_KEY = "填入你更换后的访问密钥"
$env:ECLOUD_SECRET_KEY = "填入你更换后的秘密密钥"
$env:CIM_DEVICE_ID = "WuYue-QPU-Qboson-1000"
$env:CIM_MAX_BITS = "1000"
$env:CIM_PRECISION = "8"
$env:CIM_MAX_CALLS = "1"
$env:CIM_CALL_SECONDS = "120"
$env:CIM_CACHE_DIR = "results/cim_tasks"
$env:QAIA_EXACT_MODE = "on_qaia_failure"
python -m experiments.run_instance --instance data/ev_instances_v1/v1_N6_C2_s0.json --method cim_root --seed 0 --limit 300 --out results/cim_smoke_v1/cim.json
```

最后一条命令会提交真机任务，可能使用云端配额。先确认单实例成功，再将 CIM_MAX_CALLS 调到 3，并给批量命令添加 --include-cim：

```powershell
$env:CIM_MAX_CALLS = "3"
python -m experiments.run_batch --instance data/acn_scale_pilot/2019-03-05_N12_C3.json --variant-file config/final_variants.json --qaia-config tuning/acn_train_v1/best_qaia.json --include-cim --seeds 0 1 2 --exact-repeats 3 --limit 600 --out-dir results/final_cim_pilot_v1
```

时间和规模边界：

- 每个 BP 运行最多提交 CIM_MAX_CALLS 次；每次本地等待最多 CIM_CALL_SECONDS，同时受 BP 剩余时间限制。
- 本地超时后禁止该运行继续提交 CIM，剩余时间由 Exact 使用。结束子进程不等于取消远端任务；该任务可能继续执行并消耗配额。
- CIM 任务采用 UUID 名称，避免跨重复实验复用缓存结果。BP 的 seed 影响本地随机过程，并非真机随机种子的控制参数。
- 1000 限制对应 Ising 变量数，不是车辆数。预检查使用候选顶点数加 1，转换后再检查矩阵；PrecisionReducer 的 target_bits 控制降精度阶段的目标规模。
- 超过设备上限时跳过 CIM，记录 size_skips，由 Exact 接管；本版未实现 subQUBO。大于硬件规模的结果不能拿来声称 CIM 优劣。
- SDK 错误会标为 error，不悄悄用 Greedy/模拟器伪装真机；正常超时或调用额度耗尽可以走 Exact，并保留明确诊断。
- 请求目录包含 request.json、status.json、worker.log、samples.npy（成功时）及 SDK checkpoint。不要在任务未结束时删除。程序不记录凭据到请求 JSON；SDK 自身日志归档前也应检查敏感内容。

主要诊断在 `statistics.root_diagnostics.heuristic_metrics.cim`：requests、completed、timeouts、size_skips、capped_skips、seconds、tasks。requests 是本地启动的请求尝试，不保证服务器已接收；远端是否接收以平台/checkpoint 为准。completed=0 的运行不能视作 CIM 提供了有效列。真正返回的新列数仍查看 returned_columns。

历史字段 total_qaia_time、total_qaia_calls、qaia_nodes 为兼容旧输出仍保留，实际累计的是所选启发式后端。请结合 heuristic_provider 或 root_diagnostics.heuristic_metrics.provider 判断 QAIA、Greedy 或 CIM，不能仅凭旧字段名判定算法。CIM SDK 返回样本数量由实际服务决定，记录 raw_samples；QAIA 的 batch 参数不控制该移动云 API 的采样数。

## 7. 扩大数据：固定日期，再查可用性

建议以 Caltech 单站点作为主实验，按当地到达日期分割，先冻结日期，不按 QAIA 胜负选日期。

| 用途 | 日期 |
| --- | --- |
| 训练/开发 | 2019-03-04 至 03-08，已在前期研究使用 |
| 验证 | 2019-03-11、12、13、14、15 |
| 正式测试 | 2019-03-18、19、20、21、22、25、26、27、28、29 |
| 跨月份外部测试 | 2019-04-08、09、10、11、12 |

这些是按工作周提出的预先设计，不代表已下载或已确认每一天能支持 N48。当前仓库仅有 260 条原始记录，覆盖当地日期 2019-02-28 至 03-09；新日期必须补充下载。若某天车辆不足，保留“样本不足”的审计，在该日期使用预定网格中可生成的较小 N；不要重复复制车辆、随机丢弃候选区间或按算法表现换日期。

现有文件经原转换器、15 分钟、7 kW 检查：

| 日期 | 有效车辆 | N32 候选顶点数 | 支持 N40 |
| --- | ---: | ---: | --- |
| 2019-03-04 | 37 | 593 | 否 |
| 2019-03-05 | 37 | 751 | 否 |
| 2019-03-06 | 37 | 587 | 否 |
| 2019-03-07 | 42 | 792 | 是，N40 为 857 顶点 |
| 2019-03-08 | 35 | 731 | 否 |

原始数据下载：使用 ACN 官方页面，选择 Caltech，下载覆盖 2019-03-10 至 03-31 的 sessions JSON，保存为 `data/raw/acn/caltech_march_holdout.json`。为了覆盖当地日期边界，查询 UTC 范围应留出前后一天。外部测试另下载 04-07 至 04-14 到独立文件。这里不需要 /ts 电流时间序列。使用 API 时必须收齐所有 next 分页；原转换器会拒绝残留 next 链接的不完整页面。多个页面应合并成会话列表，而非仅删除 next 字段。

处理语义沿用原代码：UTC 转站点 timezone；以当地到达日午夜为时间原点；到达向上取整、离开向下取整到 15 分钟网格；充电时长为 ceil(kWhDelivered / (7 kW × 0.25 h))。跨夜会话可以保留，超过 48 小时按既有规则排除。2019-03-10 前后有夏令时切换，必须使用 America/Los_Angeles，不能手动固定减 8 小时。

排除重复冲突记录、非法时间/能量、零能量和离散时间窗不足会话。按连接时间再按 sessionID 排序取前 N 辆；所有可行开始时刻完整枚举。kWhDelivered 是历史实际交付量，不是用户原始需求；7 kW、同质充电桩池是建模假设。这里的每日实例按“当日到达队列”定义，不包含前一日到达但仍在站内的所有车辆，因此不是完整站点每日运营重建。

原代码和新增脚本的分工：

| 文件 | 使用场景 |
| --- | --- |
| ev/acn_to_ev.py | 原始 sessions → 单日期 EV 实例 + .audit.json |
| experiments/prepare_scale.py | 按日期 × N × 车桩比批量转换，生成 instances.json |
| validation/acn_input.py | 自动复核时区、能量、时长和完整候选集合；由 check_input 调用 |
| ev/ev_to_pcp.py | 求解时将 EV 实例转成 PCP 图，不需要手动调用 |
| ev/generate_ev_instances_v1.py | 补充可控合成实例，不能当作新增真实 ACN 日期 |
| experiments/inspect_acn_dates.py | 新增的无求解器日期审计，输出 inventory.json |

审计新日期：

```powershell
python -m experiments.inspect_acn_dates --raw data/raw/acn/caltech_march_holdout.json --split validation --out-dir data/acn_inventory_validation_v1
python -m experiments.inspect_acn_dates --raw data/raw/acn/caltech_march_holdout.json --split test --out-dir data/acn_inventory_test_v1
```

审计中的每日 JSON 的 chargers=1 只用于候选计数，不要把它们当正式实验实例。正式用原 prepare_scale 生成，例如先在确认有效车辆数足够后：

```powershell
python -m experiments.prepare_scale --family acn --raw data/raw/acn/caltech_march_holdout.json --dates 2019-03-11 2019-03-12 2019-03-13 2019-03-14 2019-03-15 --sizes 16 24 32 --ratios 4 8 --slot-minutes 15 --power-kw 7 --max-vertices 3000 --out-dir data/acn_validation_final_v1
```

若某天不够 N32，先按 inventory 分开调用不同 sizes，不让程序偷偷缩小 N。prepare_scale 遇到车辆不足会报错并留下审计，已有输出目录不会覆盖。

ratio=4 表示每 4 辆车配置 1 桩，N32/C8；ratio=8 表示 N32/C4，资源更紧。N48 必须先验证日期样本量。CIM 完整子问题共同对照集应根据候选顶点数和设备上限固定，不能为了塞进设备随机裁剪候选时刻；更大实例可以作为 Exact/QAIA/Greedy 的扩展组，并清楚报告 CIM 未运行。

## 8. 正式实验和汇总

在验证日选定配置后，对测试日冻结参数，用 10 个重复种子。先做 300 秒，另开目录做 600 秒；不要覆盖已有批次。

```powershell
python -m experiments.run_batch --instance-list data/acn_validation_final_v1/instances.json --variant-file config/final_variants.json --qaia-config tuning/acn_train_v1/best_qaia.json --seeds 0 1 2 3 4 5 6 7 8 9 --exact-repeats 10 --limit 300 --out-dir results/final_validation_300_v1
python -m experiments.summarize_scale --results-dir results/final_validation_300_v1 --out-dir results/final_validation_300_summary_v1
python -m experiments.compare_anytime --results-dir results/final_validation_300_v1 --checkpoints 30 120 300 --out-dir results/final_validation_300_report_v1
```

将验证 manifest 换成由正式测试日期生成的 manifest 即执行测试。冻结文件的 training_instances、sha256、training_protocol 可追溯；单次结果 overlaps_tuning_instance/overlaps_tuning_date 提醒是否仍在训练数据上运行。程序不强行禁止训练集烟雾测试，但论文不能把重叠实例称作测试集。

每个正式实例不含 CIM 时：1 Compact + 10 Exact + 10 默认 QAIA + 10 调优 QAIA + 10 Greedy，共 41 次；300 秒预算上界约 3.4 小时/实例。加入 CIM 为 51 次，最多 30 次 CIM 请求尝试/实例（max_calls=3）。建议先做 3 个种子真机试点，确认任务返回时间和配额，再扩到 10 次。按固定顺序/交替顺序运行并记录硬件负载。

结果以可行比例、目标值中位数/四分位数、首次可行时间、incumbent 曲线为主。无解保留 null；time_limit 保留限时内已验证的解。调参耗时单独报告；CIM 网络和排队不可从在线对比中扣除。若统计设备内部耗时，只能作为另一项诊断。

## 9. 文件保留和清理

保留正式批次的 manifest、每次原始 JSON、incumbents.jsonl、诊断汇总及对应实例和源码。调参保存 best_qaia.json、trials.json、study.sqlite3 与训练运行记录。CIM checkpoint 在任务结束和核查前保留。测试失败记录也保留，不按方法输赢删除。

旧烟雾测试可在归档后清理；报告 CSV 可从原始结果重建。完整交付包不携带旧 results，不会删除你项目里的任何现有结果。不要把你本地运行产生的含密钥日志、SDK 缓存直接推到 GitHub。

## 10. 文档依据与验证边界

- MindQuantum 自动调参示例：https://mindquantum.org/docs/zh/src/case_library/qaia_automatic_parameter_adjustment.html
- Kaiwu PrecisionReducer/API 文档：https://kaiwu-sdk-docs.qboson.com/zh/v1.3.1/source/modules/kaiwu.cim.html
- CIM 移动云参数来源：用户提供的 QBendersOCT.py；该附件未打包，也未改写。
- ACN 数据定义、UTC 和分页：https://ev.caltech.edu/dataset

软件测试和本地烟雾实验见随包 VALIDATION.md。本版未实际提交 CIM 云任务，不能声称通过真机集成验收；请按 check_cim、单次小实例、少量种子试点的顺序验证你实际安装的移动云 SDK。没有将模拟器结果标为 CIM。
