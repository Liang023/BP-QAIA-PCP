"""Summary semantics: failed runs, request uncertainty, and cached batch identity."""
import json

from run.pricing_compare import _aggregate, _flatten


def _run(*, status="completed", source="new_cloud", batch="one", independent=True,
         negative_count=2, best_rc=-3.0, submissions=1):
    return dict(task_hash="frozen_task", method="cim", status=status,
        sample_source=source, batch_identity=batch, independent_repeat=independent,
        request_status=status, new_request_count=1, backend_request_attempt_count=1,
        actual_cloud_submission_count=submissions,
        replay_version=dict(source_sha256="source_version"),
        metrics=dict(raw_unique_negative_reduced_cost_count=negative_count,
                     unique_negative_reduced_cost_count=negative_count,
                     best_legal_reduced_cost=best_rc,
                     ratios=dict(raw_legality=dict(numerator=1 if negative_count else 0,
                                                  denominator=2 if negative_count else 0))),
        timing=dict(wall_seconds=1.0))


def test_failures_remain_in_count_means_and_unknown_submissions_stay_visible():
    runs = [_run(negative_count=5),
            _run(status="error", batch=None, negative_count=0, best_rc=None, submissions=None),
            _run(status="empty", batch="empty", negative_count=0, best_rc=None, submissions=0)]
    row = _aggregate(runs)[0]
    assert row["run_count"] == 3
    assert json.loads(row["status_counts"]) == {"completed": 1, "error": 1, "empty": 1}
    assert row["metrics.raw_unique_negative_reduced_cost_count.sum"] == 5
    assert row["metrics.raw_unique_negative_reduced_cost_count.mean_all_runs"] == 5/3
    assert row["metrics.unique_negative_reduced_cost_count.sum"] == 5
    assert row["metrics.best_legal_reduced_cost.observed_runs"] == 1
    assert row["metrics.best_legal_reduced_cost.mean_observed"] == -3.0
    assert row["ratio.raw_legality.numerator_sum"] == 1
    assert row["ratio.raw_legality.denominator_sum"] == 2
    assert row["ratio.raw_legality.pooled_value"] == 0.5
    assert row["actual_cloud_submission_count_known_sum"] == 1
    assert row["actual_cloud_submission_count_observed_runs"] == 2
    assert row["actual_cloud_submission_count_unknown_runs"] == 1
    assert "actual_cloud_submission_count_sum" not in row


def test_duplicate_batches_are_not_new_repeats_and_cache_is_a_separate_group():
    runs = [_run(batch="same"), _run(batch="same"), _run(batch="second"),
            _run(status="error", batch=None, submissions=None),
            _run(source="cached_cloud", batch="same", independent=False, submissions=0),
            _run(source="cached_cloud", batch="same", independent=False, submissions=0)]
    rows = {row["sample_source"]: row for row in _aggregate(runs)}
    assert len(rows) == 2
    fresh = rows["new_cloud"]
    assert fresh["run_count"] == 4
    assert fresh["independent_attempt_count"] == 4
    assert fresh["independent_repeat_count"] == 2
    assert fresh["unique_raw_batch_count"] == 2
    assert fresh["actual_cloud_submission_count_unknown_runs"] == 1
    cached = rows["cached_cloud"]
    assert cached["run_count"] == 2
    assert cached["independent_attempt_count"] == 0
    assert cached["independent_repeat_count"] == 0
    assert cached["unique_raw_batch_count"] == 1
    assert cached["actual_cloud_submission_count_known_sum"] == 0


def test_flat_rows_preserve_unknown_counts_and_source_identity():
    row = _flatten(_run(submissions=None))
    assert row["actual_cloud_submission_count"] is None
    assert row["metrics.raw_unique_negative_reduced_cost_count"] == 2
    assert row["replay_version.source_sha256"] == "source_version"
