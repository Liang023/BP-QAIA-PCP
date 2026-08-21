# Partition Coloring Problem (Branch-and-Price)

This repository implements a Branch-and-Price framework for the Partition Coloring Problem (PCP), including the Restricted Master Problem (RMP), pricing subproblem, column generation loop, and branching rules.

## Features
- Master problem: modeled in Gurobi; supports exporting LP for debugging
- Pricing: exact pricing solver (maximum weight stable set) with solution pool and reduced-cost assertion (`BPC_DEBUG=1`)
- Column generation: iteratively introduces columns with negative reduced cost based on duals
- Branching: supports imposed vertex, forbid vertex, same-color and different-color branching rules

## Requirements
- Python 3.8+
- Gurobi 10.x (license configured)

## Installation
- Via pip (requires a valid Gurobi license):
```bash
pip install gurobipy
```
- Or via conda:
```bash
conda install -c gurobi gurobi
```

## Data
- Test instances under `data/Table2_random_instances/*.pcp`
- Reader: `test/pcp_reader.py` parses `.pcp` and builds the graph

## Run
- Run the test driver:
```bash
python -m test.test_bp
```
- VS Code debug (example `.vscode/launch.json`):
  - Working directory: project root
  - Env: `PYTHONPATH=${workspaceFolder}`; enable reduced-cost assertion via `BPC_DEBUG=1`

## Key Modules
- `cg/master/master_problem.py`: RMP modeling and solve
- `cg/pricing/exact_pricing_solver.py`: exact pricing solver
- `cg/column_generation.py`: column generation main loop
- `bpc/branching/*`: branching decisions
- `model/a_graph.py`: auxiliary graph structure and operations

## License
MIT, see `LICENSE`.
