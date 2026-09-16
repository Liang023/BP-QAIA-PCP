"""A primal heuristic on current real columns. It never certifies a BP bound."""
import time
import gurobipy as gp
from cg.deadline import remaining_seconds


def solve_restricted_mip(master, deadline, seconds, on_candidate):
    started = time.perf_counter()
    if seconds <= 0:
        return 0.0
    local_deadline = min(deadline, started + seconds)
    model = None
    errors = []
    try:
        remaining_seconds(local_deadline, "Before restricted MIP copy")
        master._rmp.update()
        model = master._rmp.copy()
        model.Params.OutputFlag = 0
        model.Params.Threads = 1
        model.Params.Seed = 0
        model.Params.MIPGap = 0.0
        model.Params.MIPGapAbs = 0.0
        real = []
        for mapping in master.varMap.values():
            for column, old_var in mapping.items():
                variable = model.getVarByName(old_var.VarName)
                variable.VType = gp.GRB.BINARY
                variable.UB = 0 if column.is_artificial_column else 1
                if not column.is_artificial_column:
                    real.append((column, variable))
        model.update()
        variables = [v for _, v in real]

        def callback(m, where):
            if where != gp.GRB.Callback.MIPSOL:
                return
            if time.perf_counter() > deadline:
                m.terminate()
                return
            try:
                values = m.cbGetSolution(variables)
                solution = {c: float(x) for (c, _), x in zip(real, values) if x > 1e-6}
                on_candidate(solution, float(m.cbGet(gp.GRB.Callback.MIPSOL_OBJ)))
            except Exception as exc:
                errors.append(exc)
                m.terminate()

        model.Params.TimeLimit = remaining_seconds(local_deadline, "Restricted MIP")
        model.optimize(callback)
        if errors:
            raise errors[0]
        # A local heuristic timeout may still leave enough *global* time to validate.
        if model.SolCount and time.perf_counter() <= deadline:
            on_candidate({c: float(v.X) for c, v in real if v.X > 1e-6}, float(model.ObjVal))
    except TimeoutError:
        # Exhausting this small local heuristic budget is not a global BP failure.
        if time.perf_counter() >= deadline:
            raise
    finally:
        if model is not None:
            model.dispose()
    return time.perf_counter() - started
