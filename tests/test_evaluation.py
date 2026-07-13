"""test_evaluation.py - deterministic tests for the Phase 7 eval harness.

The metric computations and example building are tested offline (no LLM). The
live end-to-end scoring is exercised by tests/test_evals.ipynb.
"""

from app.modules import evaluation


def test_compute_metrics_perfect():
    y = ["continue", "schedule", "end"]
    metrics = evaluation.compute_metrics(y, y)
    assert metrics["accuracy"] == 1.0
    # diagonal confusion matrix
    cm = metrics["confusion_matrix"]
    assert cm.trace() == len(y)


def test_compute_metrics_counts_errors():
    y_true = ["continue", "schedule", "end", "end"]
    y_pred = ["continue", "schedule", "continue", "end"]
    metrics = evaluation.compute_metrics(y_true, y_pred)
    assert abs(metrics["accuracy"] - 0.75) < 1e-9


def test_find_errors_lists_mismatches():
    examples = [
        {"conversation_id": 1, "turn_id": 3, "history": [{"speaker": "candidate", "text": "hi"}]},
        {"conversation_id": 1, "turn_id": 5, "history": [{"speaker": "candidate", "text": "bye"}]},
    ]
    errors = evaluation.find_errors(examples, ["end", "continue"], ["continue", "continue"])
    assert len(errors) == 1
    assert errors[0]["turn_id"] == 3
    assert errors[0]["actual"] == "end" and errors[0]["predicted"] == "continue"


def test_build_eval_examples_shape():
    examples = evaluation.build_eval_examples()
    assert len(examples) == 44  # labeled recruiter turns with history
    for e in examples:
        assert e["label"] in ("continue", "schedule", "end")
        assert len(e["reference_date"]) == 10  # YYYY-MM-DD
        assert e["history"]  # non-empty
