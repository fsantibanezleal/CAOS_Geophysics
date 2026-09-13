from __future__ import annotations


def run(case_ids: list[str]) -> dict:
    ordered = sorted(case_ids)
    cut = max(1, int(len(ordered) * 0.7))
    return {"train": ordered[:cut], "validation": ordered[cut:max(cut + 2, cut)], "test": ordered[max(cut + 2, cut):], "split_policy": "case-id grouped; no observation from a case crosses a split"}
