# BP–QAIA–CIM 分支定价实验代码

本版支持 Compact MILP、Exact BP、Greedy/QAIA/CIM 混合定价、根节点互补列和限时可行解轨迹。

完整安装、离线 Optuna 调参、CIM 配置、Windows PowerShell 命令、数据日期划分和实验步骤，请阅读 [README_FINAL.md](README_FINAL.md)。验证记录见 [VALIDATION.md](VALIDATION.md)。

调参是独立阶段，不计入后续正式 BP 求解时间。CIM 在线调用和等待计入 BP 时间预算。CIM 接口按用户提供的移动云版 QBendersOCT.py 适配，真机验收需在该 SDK 环境执行。

```powershell
python -m pip install -r requirements-final.txt
python -m pytest -q
```

基于仓库提交 `231fe9c9c744d679ded0c6d121d79e2b4a032ad0`。许可证见 LICENSE；qaia 中保留上游文件的授权说明。
