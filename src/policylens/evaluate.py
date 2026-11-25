"""Compare detected statuses with a hand-labelled answer key.

Answer key CSV columns: req_id,label   (label = covered | partial | gap)
Generate a blank one with: policylens init-key <standard-id>
"""
import itertools
from pathlib import Path

import pandas as pd

from .gap import label_from_score

LABELS = ["covered", "partial", "gap"]


def init_answer_key(requirements, out="data/eval/answer_key.csv"):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"req_id": [r["req_id"] for r in requirements], "label": ""}
    ).to_csv(out, index=False)
    return out


def load_key(path):
    key = pd.read_csv(path, dtype=str).fillna("")
    key["label"] = key["label"].str.strip().str.lower()
    blank = (key["label"] == "").sum()
    if blank:
        raise ValueError(
            f"{blank} rows in {path} have no label yet. Fill every row with "
            f"one of: {', '.join(LABELS)}."
        )
    bad = key[~key["label"].isin(LABELS)]
    if len(bad):
        raise ValueError(f"Invalid labels: {sorted(set(bad['label']))}")
    return key


def metrics(true, pred):
    """Per-class precision/recall/F1, macro-F1 and accuracy (no sklearn needed)."""
    out, f1s = {}, []
    for lab in LABELS:
        tp = sum(t == lab and p == lab for t, p in zip(true, pred))
        fp = sum(t != lab and p == lab for t, p in zip(true, pred))
        fn = sum(t == lab and p != lab for t, p in zip(true, pred))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[lab] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
        f1s.append(f1)
    out["macro_f1"] = sum(f1s) / len(f1s)
    out["accuracy"] = (
        sum(t == p for t, p in zip(true, pred)) / len(true) if true else 0.0
    )
    return out


def evaluate(report_df, key_df):
    merged = key_df.merge(report_df[["req_id", "status", "score"]], on="req_id")
    if merged.empty:
        raise ValueError("No req_id overlap between the report and the answer key.")
    missing = set(key_df["req_id"]) - set(report_df["req_id"])
    if missing:
        print(f"Note: {len(missing)} key rows are not in the report: {sorted(missing)[:5]}...")
    return metrics(merged["label"].tolist(), merged["status"].tolist()), merged


def sweep_thresholds(report_df, key_df, covered_values=None, partial_values=None):
    """Grid-search thresholds using the scores already in the report.

    No re-embedding needed. Beware of overfitting: with a small key, tune on
    one half and report on the other half.
    """
    merged = key_df.merge(report_df[["req_id", "score"]], on="req_id")
    covered_values = covered_values or [round(x / 100, 2) for x in range(40, 81, 5)]
    partial_values = partial_values or [round(x / 100, 2) for x in range(20, 66, 5)]
    rows = []
    for c, p in itertools.product(covered_values, partial_values):
        if p >= c:
            continue
        preds = [label_from_score(s, c, p) for s in merged["score"].astype(float)]
        m = metrics(merged["label"].tolist(), preds)
        rows.append(
            {
                "covered_th": c,
                "partial_th": p,
                "macro_f1": round(m["macro_f1"], 3),
                "accuracy": round(m["accuracy"], 3),
                "gap_recall": round(m["gap"]["recall"], 3),
                "gap_precision": round(m["gap"]["precision"], 3),
            }
        )
    return pd.DataFrame(rows).sort_values("macro_f1", ascending=False).reset_index(drop=True)


def format_metrics(m):
    lines = [f"{'class':<9}{'prec':>7}{'recall':>8}{'f1':>7}{'n':>5}"]
    for lab in LABELS:
        r = m[lab]
        lines.append(
            f"{lab:<9}{r['precision']:>7.2f}{r['recall']:>8.2f}{r['f1']:>7.2f}{r['support']:>5}"
        )
    lines.append(f"macro-F1 {m['macro_f1']:.2f} | accuracy {m['accuracy']:.2f}")
    return "\n".join(lines)
