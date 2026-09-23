"""Offline clock checks: no cloud credentials or cloud requests are used."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from cg import budget_clock
from cg.anytime import IncumbentRecorder, snapshots
from cg.deadline import remaining_seconds
from cg.pricing.cim_backend import CIMBackend


class CIMClockTests(unittest.TestCase):
    def setUp(self):
        budget_clock.reset()

    def tearDown(self):
        budget_clock.reset()

    def test_long_cloud_wait_preserves_deadline_and_checkpoints(self):
        raw = [100.0]
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
                "CIM_CACHE_DIR": folder, "CIM_MAX_CALLS": "2",
                "ECLOUD_ACCESS_KEY": "test", "ECLOUD_SECRET_KEY": "test"}), \
                patch("time.perf_counter", side_effect=lambda: raw[0]):
            recorder = IncumbentRecorder(100, 110, wall_start_time=100)

            def worker(command, **kwargs):
                self.assertNotIn("timeout", kwargs)
                raw[0] += 400.6  # 400 cloud seconds, 0.6 local seconds
                target = Path(command[-1])
                np.save(target, np.array([[1]], dtype=np.int8))
                (target.parent / "cloud_timing.json").write_text(
                    json.dumps(dict(cloud_call_seconds=400)))
                return SimpleNamespace(returncode=0)

            backend = CIMBackend()
            with patch("subprocess.run", side_effect=worker):
                for value in (2, 1):
                    samples = backend.sample([0], {0: 2}, {0: set()}, set(), 1, 110)
                    self.assertEqual(samples.shape, (1, 1))
                    self.assertTrue(recorder.record([[value]], value, "test"))
            self.assertAlmostEqual(remaining_seconds(110, "after two calls"), 8.8)
            self.assertAlmostEqual(recorder.history[-1]["elapsed_seconds"], 1.2)
            self.assertAlmostEqual(recorder.history[-1]["wall_elapsed_seconds"], 801.2)
            self.assertEqual(snapshots(recorder.history, [10])[0]["objective"], 1)
            raw[0] += 9
            with self.assertRaises(TimeoutError):
                remaining_seconds(110, "local work exhausted budget")

    def test_cloud_error_is_reported_not_replaced_by_empty_samples(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
                "CIM_CACHE_DIR": folder, "ECLOUD_ACCESS_KEY": "test",
                "ECLOUD_SECRET_KEY": "test"}), \
                patch("subprocess.run", return_value=SimpleNamespace(returncode=1)):
            backend = CIMBackend()
            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                backend.sample([0], {0: 2}, {0: set()}, set(), 1, budget_clock.now()+10)
            self.assertEqual(backend.metrics["completed"], 0)


if __name__ == "__main__":
    unittest.main()
