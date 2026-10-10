# BP–QAIA–CIM 分支定价实验代码

本版支持 Compact MILP、Exact BP、Greedy/QAIA/CIM 混合定价、根节点互补列和限时可行解轨迹。

固定定价任务的采集、重放、CIM 配置及 PowerShell 命令见 [定价对照说明](docs/pricing_comparison.md)，已有实验的验证记录见 [定价对照验证](results/pricing_comparison_local_20261002/VALIDATION.md)。

调参是独立阶段，不计入后续正式 BP 求解时间。完整 BP 实验的时间预算排除阻塞的 CIM 云调用；固定任务重放另记录包含等待的墙钟时间。CIM 使用单独提供的移动云 eCloud Kaiwu SDK。

```powershell
python -m pip install -r requirements-final.txt
python -m pytest -q
```

主要入口与依赖：

- `experiments.prepare_scale`：从 ACN 数据生成 EV 算例；日期划分见 `config/acn_final_split.json`。
- `experiments.run_instance`：单个算例求解，调用 `ev/` 建图、`bpc/` 分支、`cg/` 主问题和定价；解验证位于 `validation/`。
- `experiments.run_batch`：批量运行与逐次结果记录；`experiments.summarize_scale` 和 `experiments.compare_anytime` 读取这些结果生成汇总。
- `run.run`：完整对照流程，默认使用 `data/instances/instances.json`、`config/qaia_candidates_v3.json` 和 `config/cim_only.json`，输出到 `results/result_c5_v1`。该配置包含真实 CIM 调用。
- `experiments.tune_qaia`：离线调参，冻结配置供后续实验使用；`qaia/` 保留上游算法和授权说明。
- `run.pricing_compare`：固定任务的采集、重放和汇总，命令见上面的定价对照说明。

各入口的参数可通过 `python -m <模块名> --help` 查看。Gurobi 相关测试需要匹配当前用户的有效许可证。

结果保留策略与本次清理明细见 [清理记录](docs/cleanup_20261009.md)。

基于仓库提交 `231fe9c9c744d679ded0c6d121d79e2b4a032ad0`。许可证见 LICENSE；qaia 中保留上游文件的授权说明。
