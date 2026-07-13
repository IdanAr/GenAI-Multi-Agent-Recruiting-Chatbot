"""evaluation.py - Phase 7 evaluation harness.

Runs the full multi-agent system over the labeled conversations and compares the
Main Agent's predicted action (Continue / Schedule / End) against the label at
each recruiter turn. Provides Accuracy, a Confusion Matrix, a per-class report,
and an error list for analysis.

The heavy logic lives here so tests/test_evals.ipynb stays thin.
"""

import json
from datetime import date

from app.modules import config
from app.modules.main_agent import decide_action

# Fixed action order for the confusion matrix axes.
ACTIONS = ["continue", "schedule", "end"]

# Conversations 1-5 seeded the Exit Advisor's few-shot examples. Held-out
# evaluation therefore uses conversations 6-15 to avoid that overlap.
FEWSHOT_POOL_IDS = set(range(1, 6))


def build_eval_examples(include_openers: bool = False,
                        held_out_only: bool = False) -> list[dict]:
    """Build labeled evaluation examples from sms_conversations.json.

    Each example is a recruiter turn with the history that precedes it and the
    correct action label. Opening recruiter turns (no candidate message yet) are
    skipped by default. With held_out_only, conversations 1-5 (the few-shot pool)
    are excluded.
    """
    data = json.loads(config.CONVERSATIONS_JSON.read_text(encoding="utf-8"))
    examples = []
    for conv in data:
        if held_out_only and conv["conversation_id"] in FEWSHOT_POOL_IDS:
            continue
        turns = conv["turns"]
        for i, turn in enumerate(turns):
            if turn["speaker"] != "recruiter" or turn["label"] is None:
                continue
            if i == 0 and not include_openers:
                continue
            reference_date = (turn.get("timestamp_utc", "")[:10]
                              or date.today().isoformat())
            examples.append({
                "history": turns[:i],
                "label": turn["label"],
                "reference_date": reference_date,
                "conversation_id": conv["conversation_id"],
                "turn_id": turn["turn_id"],
            })
    return examples


def predict_actions(examples: list[dict], llm=None, progress: bool = True) -> list[str]:
    """Predict the Main Agent action for each example (one live turn each)."""
    predictions = []
    total = len(examples)
    for k, example in enumerate(examples, start=1):
        try:
            result = decide_action(example["history"],
                                   reference_date=example["reference_date"], llm=llm)
            action = result["action"]
        except Exception:
            action = "continue"  # safe fallback so one bad turn cannot abort the run
        predictions.append(action)
        if progress:
            print(f"[{k:2}/{total}] conv{example['conversation_id']:>2} "
                  f"turn{example['turn_id']:>2}  label={example['label']:<9} "
                  f"pred={action}")
    return predictions


def compute_metrics(y_true: list[str], y_pred: list[str], labels=ACTIONS) -> dict:
    """Compute accuracy, confusion matrix, and a per-class report (sklearn)."""
    from sklearn.metrics import (accuracy_score, confusion_matrix,
                                 classification_report)

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels),
        "labels": labels,
        "report": classification_report(y_true, y_pred, labels=labels,
                                         zero_division=0),
    }


def find_errors(examples: list[dict], y_true: list[str], y_pred: list[str]) -> list[dict]:
    """Return the misclassified turns for error analysis."""
    errors = []
    for example, actual, predicted in zip(examples, y_true, y_pred):
        if actual != predicted:
            last_msg = example["history"][-1]["text"] if example["history"] else ""
            errors.append({
                "conversation_id": example["conversation_id"],
                "turn_id": example["turn_id"],
                "actual": actual,
                "predicted": predicted,
                "last_candidate_msg": last_msg,
            })
    return errors


def run_evaluation(held_out_only: bool = False, llm=None, progress: bool = True) -> dict:
    """Build examples, predict, and return everything needed to report."""
    examples = build_eval_examples(held_out_only=held_out_only)
    y_true = [e["label"] for e in examples]
    y_pred = predict_actions(examples, llm=llm, progress=progress)
    metrics = compute_metrics(y_true, y_pred)
    metrics["examples"] = examples
    metrics["y_true"] = y_true
    metrics["y_pred"] = y_pred
    metrics["errors"] = find_errors(examples, y_true, y_pred)
    return metrics
