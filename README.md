# Partition Coloring Problem (Branch-and-Price)

本项目实现了分区着色问题（PCP）的分支定价（Branch-and-Price）求解框架，包含主问题（RMP）、定价子问题、列生成流程与分支规则。

## 特性
- 主问题：Gurobi 建模，支持导出 LP 供调试
- 定价：精确定价求解器（最大权稳定集），支持解池与 reduced cost 调试断言（设置环境变量 `BPC_DEBUG=1`）
- 列生成：按对偶信息迭代生成负 reduced cost 列
- 分支：支持强制顶点、禁止顶点、同色/异色等分支规则

## 环境要求
- Python 3.8+
- Gurobi 10.x（已配置 license）

## 依赖安装
- 使用 pip（需先配置好 Gurobi 许可）：
```bash
pip install gurobipy
```
- 或使用 conda：
```bash
conda install -c gurobi gurobi
```

## 数据
- 测试数据位于 `data/Table2_random_instances/*.pcp`
- `test/pcp_reader.py` 提供 `.pcp` 读取与图构建

## 运行
- 直接运行测试脚本：
```bash
python -m test.test_bp
```
- VS Code 调试（`.vscode/launch.json` 示例）：
  - Working directory: 项目根
  - 环境变量：`PYTHONPATH=${workspaceFolder}`；调试断言可加 `BPC_DEBUG=1`

## 关键模块
- `cg/master/master_problem.py`：主问题建模与求解
- `cg/pricing/exact_pricing_solver.py`：精确定价求解器
- `cg/column_generation.py`：列生成主循环
- `bpc/branching/*`：分支决策实现
- `model/a_graph.py`：辅助图数据结构与操作


## 许可证
见 `LICENSE`（MIT）。
