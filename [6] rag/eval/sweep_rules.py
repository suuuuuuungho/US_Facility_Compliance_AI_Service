"""SUU-132: 리랭크 전체 순위(ranked_all)에 창·규칙을 적용해 $0으로 채점한다.

사용법 (레포 루트에서):
  python "[6] rag/eval/sweep_rules.py" --run-id 2026-09-18_hybrid_v2   # → results/rules_sweep.csv + 요약 출력

규칙:
- 창(window): 규칙을 적용할 순위 범위. 창 밖은 그대로 둔다.
- 표 뒤로(demote_tables): 창 안의 appendix-Table 조문을 맨 뒤로(서로 순서는 유지).
- Subpart 우선(subpart_top): 1~5등에 나온 Subpart 상위 n개 + Subpart A 조문을 앞으로, 나머지는 뒤로. 0이면 끔.
채점은 `[1] docs/1) project/1_full/1_Project_full.md` "RAG 검색 품질 개선 과정" 절 채점표(Hit@5·Hit@20·nDCG@10·Recall@20)와 같고, 창 20 + 규칙 없음 = 원래 결과.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
SWEEP_CSV = RESULTS / "rules_sweep.csv"
GRID = {"window": [20, 30, 40, 60, None], "demote_tables": [False, True], "subpart_top": [0, 1, 2]}
K_MAX = 20


def is_table(section_key: str) -> bool:
    return "Table" in section_key


def apply_rules(ranked: list[list], *, window: int | None, demote_tables: bool, subpart_top: int) -> list[list]:
    """ranked = [[section_key, subpart, ...], ...] 앞이 1등. 창 안만 재정렬해 돌려준다."""
    head, tail = (ranked[:window], ranked[window:]) if window else (list(ranked), [])
    if subpart_top:
        found: list[str] = []
        for row in head[:5]:
            if row[1] not in found:
                found.append(row[1])
        keep = set(found[:subpart_top]) | {"A"}
        head = [r for r in head if r[1] in keep] + [r for r in head if r[1] not in keep]
    if demote_tables:
        head = [r for r in head if not is_table(r[0])] + [r for r in head if is_table(r[0])]
    return head + tail


def score(gold: list[str], ranked: list[list]) -> dict:
    ranks = {g: next((i + 1 for i, r in enumerate(ranked[:K_MAX]) if r[0] == g), None) for g in gold}
    within = lambda k: [r is not None and r <= k for r in ranks.values()]  # noqa: E731
    dcg = sum(1 / math.log2(r + 1) for r in ranks.values() if r is not None and r <= 10)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(gold), 10)))
    return {"hit@5": any(within(5)), "hit@20": any(within(20)), "ndcg@10": dcg / ideal, "recall@20": sum(within(20)) / len(gold)}


def sweep_table(cases: list[dict]) -> list[dict]:
    """cases: {gold, ranked} → 창 5 × 표 2 × Subpart 3 = 30행."""
    rows = []
    for window in GRID["window"]:
        for demote in GRID["demote_tables"]:
            for top in GRID["subpart_top"]:
                scores = [score(c["gold"], apply_rules(c["ranked"], window=window, demote_tables=demote, subpart_top=top)) for c in cases]
                row = {"window": window or "all", "tables": demote, "subpart": top}
                for m in ("hit@5", "hit@20", "ndcg@10", "recall@20"):
                    row[m] = round(sum(s[m] for s in scores) / len(scores), 4)
                rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    lines = [json.loads(l) for l in (RESULTS / f"{args.run_id}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = [{"case_id": l["case_id"], "gold": l["gold_sections"], "ranked": l["ranked_all"]} for l in lines]
    rows = sweep_table(cases)
    with SWEEP_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    base = rows[0]
    print(f"cases {len(cases)} → {SWEEP_CSV.name} ({len(rows)} rows)")
    print("base (window 20, no rules):", base)
    print("best 8 by ndcg@10:")
    for r in sorted(rows, key=lambda r: -r["ndcg@10"])[:8]:
        print(f"  {r}  ({r['ndcg@10'] - base['ndcg@10']:+.4f})")
    # 부분집합 확인(v1 32 / 새 70)과 케이스별 좋아짐·나빠짐 — 최고 설정 기준
    best = max(rows, key=lambda r: r["ndcg@10"])
    v1_ids = {json.loads(l)["case_id"] for l in (Path(__file__).parent / "rag_eval_case.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    kw = dict(window=None if best["window"] == "all" else best["window"], demote_tables=best["tables"], subpart_top=best["subpart"])
    up = dn = 0
    for name, sub in (("v1 32", [c for c in cases if c["case_id"] in v1_ids]), ("new 70", [c for c in cases if c["case_id"] not in v1_ids])):
        b = sum(score(c["gold"], c["ranked"])["ndcg@10"] for c in sub) / len(sub)
        a = sum(score(c["gold"], apply_rules(c["ranked"], **kw))["ndcg@10"] for c in sub) / len(sub)
        print(f"  {name}: {b:.3f} → {a:.3f} ({a - b:+.3f})")
    for c in cases:
        d = score(c["gold"], apply_rules(c["ranked"], **kw))["ndcg@10"] - score(c["gold"], c["ranked"])["ndcg@10"]
        up += d > 1e-9
        dn += d < -1e-9
    print(f"  best setting: up {up} / down {dn} / same {len(cases) - up - dn}")


if __name__ == "__main__":
    main()
