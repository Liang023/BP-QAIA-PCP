"""Run with: python -m unittest discover -s tests -p test_capacity_bounds.py"""
import itertools
import os
import random
import time
import unittest
from unittest.mock import patch

from bpc.branch_and_price import BranchAndPrice
from cg.makespan_bounds import capacity_bound
from ev.ev_to_pcp import ev_json_to_instance


def instance(options, chargers):
    vehicles = [dict(id=i, duration=choices[0][1]-choices[0][0], candidates=[
        dict(candidate_id=j, start=a, end=b) for j, (a, b) in enumerate(choices)])
        for i, choices in enumerate(options)]
    return dict(num_vehicles=len(vehicles), num_chargers=chargers, vehicles=vehicles,
                time_horizon=max(b for choices in options for _, b in choices))


def enumerated_optimum(options, chargers):
    feasible = [max(b for _, b in chosen) for chosen in itertools.product(*options)
        if all(sum(a <= t < b for a, b in chosen) <= chargers for t, _ in chosen)]
    return min(feasible) if feasible else None


class CapacityBoundTests(unittest.TestCase):
    def test_bound_against_exhaustive_candidate_enumeration(self):
        rng = random.Random(701)
        feasible_count = 0
        for _ in range(40):
            options = []
            for _ in range(4):
                duration = rng.randint(1, 3)
                options.append([(s, s+duration) for s in sorted(rng.sample(range(6), 3))])
            chargers = rng.choice([1, 2])
            opt = enumerated_optimum(options, chargers)
            data = instance(options, chargers)
            graph = ev_json_to_instance(data).graph
            bound = capacity_bound(graph, chargers, time.perf_counter()+5)
            if opt is not None:
                feasible_count += 1
                self.assertLessEqual(bound['lower_bound'], opt)
                self.assertTrue(all(h < opt for h in bound['infeasible_horizons']))
        self.assertGreater(feasible_count, 10)

    def test_analytic_bound_with_lp_disabled(self):
        graph = ev_json_to_instance(instance([[(s,s+2) for s in range(5)]]*3, 1)).graph
        bound = capacity_bound(graph, 1, time.perf_counter()+5, lp_seconds=0)
        self.assertEqual(bound['lower_bound'], 6)
        self.assertEqual(bound['lp_calls'], 0)

    def test_expired_budget_does_not_run_lp(self):
        graph = ev_json_to_instance(instance([[(0,1),(1,2)]]*2, 1)).graph
        bound = capacity_bound(graph, 1, time.perf_counter()-1)
        self.assertEqual(bound['lp_calls'], 0)
        self.assertEqual(bound['lower_bound'], 2)

    def test_bp_optimality_from_validated_incumbent(self):
        data = instance([[(s,s+1) for s in range(5)]]*4, 1)
        graph = ev_json_to_instance(data).graph
        with patch.dict(os.environ, {'BPC_CAPACITY_BOUND':'1', 'BPC_RMP_MIP':'1',
                                    'EXACT_POOL_SEARCH_MODE':'0'}):
            bp = BranchAndPrice(graph, 1, time_limit=5, use_qaia=False)
            result = bp.solve()
        self.assertEqual(result['status'], 'optimal', result['error'])
        self.assertEqual(result['objective_value'], 4)
        self.assertEqual(result['statistics']['gap'], 0)
        self.assertEqual(result['statistics']['proof_source'],
                         'validated_incumbent_matches_global_bound')

    def test_frontier_bound_cannot_exceed_incumbent(self):
        from types import SimpleNamespace
        bp = object.__new__(BranchAndPrice)
        bp.node_queue = [SimpleNamespace(objective_value=8)]
        bp.problem_lower_bound = 3
        bp.best_objective = 7
        bp.best_solution = {'found':1}
        bp.update_global_lower_bound()
        self.assertEqual(bp.global_lower_bound, 7)


if __name__ == '__main__':
    unittest.main()
