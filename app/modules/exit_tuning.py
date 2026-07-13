"""exit_tuning.py - Phase 5 evaluation of the Exit Advisor.

Compares the naive engineered prompt against the few-shot prompt on a held-out
slice of the labeled data, to decide (and document) whether the few-shot
examples improve end-of-conversation detection. No fine-tuning is involved.

Split (by conversation, to avoid leakage):
- conversations 1-5  -> few-shot pool (source of the mined examples)
- conversations 6-15 -> held-out test set (used only for measurement here)

Run the comparison:
    python -m app.modules.exit_tuning
"""

import json

from app.modules import config
from app.modules.advisors import exit_advisor
from app.prompts.exit_advisor import EXIT_ADVISOR_SYSTEM, NAIVE_EXIT_SYSTEM
from app.prompts.exit_fewshot import EXIT_FEWSHOT

POOL_CONVERSATION_IDS = set(range(1, 6))  # 1-5 are the few-shot pool.


def build_test_examples() -> list[dict]:
    """Build held-out (history, is_end) examples from conversations 6-15."""
    data = json.loads(config.CONVERSATIONS_JSON.read_text(encoding="utf-8"))
    examples = []
    for conv in data:
        if conv["conversation_id"] in POOL_CONVERSATION_IDS:
            continue
        turns = conv["turns"]
        for i, turn in enumerate(turns):
            if turn["speaker"] == "recruiter" and turn["label"] is not None and i > 0:
                examples.append({
                    "history": turns[:i],
                    "is_end": turn["label"] == "end",
                    "label": turn["label"],
                    "conversation_id": conv["conversation_id"],
                    "turn_id": turn["turn_id"],
                })
    return examples


def evaluate(examples: list[dict], few_shot_text: str = "",
             system_prompt: str = EXIT_ADVISOR_SYSTEM) -> dict:
    """Run the Exit Advisor over examples and score end-detection agreement."""
    tp = fp = fn = tn = 0
    for example in examples:
        result = exit_advisor.run_exit_advisor(example["history"],
                                               few_shot_text=few_shot_text,
                                               system_prompt=system_prompt)
        predicted_end = result["should_end"]
        actual_end = example["is_end"]
        if predicted_end and actual_end:
            tp += 1
        elif predicted_end and not actual_end:
            fp += 1
        elif not predicted_end and actual_end:
            fn += 1
        else:
            tn += 1

    n = len(examples)
    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "n": n, "accuracy": accuracy, "precision": precision,
        "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def _print_scores(title: str, scores: dict) -> None:
    print(f"{title}")
    print(f"  accuracy : {scores['accuracy']:.3f}  ({scores['tp'] + scores['tn']}/{scores['n']})")
    print(f"  end P/R/F1: {scores['precision']:.3f} / {scores['recall']:.3f} / {scores['f1']:.3f}")
    print(f"  confusion: tp={scores['tp']} fp={scores['fp']} fn={scores['fn']} tn={scores['tn']}")


def main() -> None:
    examples = build_test_examples()
    print(f"Held-out test set: {len(examples)} labeled turns "
          f"(conversations {sorted(set(e['conversation_id'] for e in examples))})\n")

    naive = evaluate(examples, few_shot_text="", system_prompt=NAIVE_EXIT_SYSTEM)
    _print_scores("NAIVE prompt (minimal instruction, no few-shot):", naive)
    print()
    engineered = evaluate(examples, few_shot_text=EXIT_FEWSHOT,
                          system_prompt=EXIT_ADVISOR_SYSTEM)
    _print_scores("ENGINEERED prompt (role + instructions + few-shot):", engineered)
    print()

    delta = engineered["accuracy"] - naive["accuracy"]
    winner = "ENGINEERED" if engineered["accuracy"] >= naive["accuracy"] else "NAIVE"
    print(f"Accuracy delta (engineered - naive): {delta:+.3f}")
    print(f"Winner: {winner}")


if __name__ == "__main__":
    main()
