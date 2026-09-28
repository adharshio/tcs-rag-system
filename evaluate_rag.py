#!/usr/bin/env python3
"""
Evaluate the Campus Placement RAG system against golden_test_set.json.

Usage:
  pip install requests
  python evaluate_rag.py --mock                              # test the script itself, no server needed
  python evaluate_rag.py --url http://localhost:8000         # real backend
  python evaluate_rag.py --url https://staging.example.com --token <JWT> --variants
  python evaluate_rag.py --url ... --only-verified --out results/run_after_fix

Expected API (agreed with Team 3):
  POST {url}/api/chat
  body:     {"question": "...", "history": [{"role": "...", "content": "..."}]}   (history optional)
  response: {"answer": "...", "sources": ["Doc A", "Doc B"]}
  Optional: "retrieved_chunks": [{"source": "Doc A", "text": "..."}]  -> used for true retrieval hit rate
"""
import argparse
import csv
import json
import re
import statistics
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------------
# 1. Calling the system
# ----------------------------------------------------------------------------

def call_api(url, question, history, token, timeout=60):
    import requests  # imported here so --mock works without it installed

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"question": question}
    if history:
        payload["history"] = history

    start = time.perf_counter()
    try:
        r = requests.post(f"{url.rstrip('/')}/api/chat", json=payload,
                          headers=headers, timeout=timeout)
        latency = time.perf_counter() - start
        try:
            data = r.json()
        except ValueError:
            data = {}
        return {
            "status": r.status_code,
            "answer": data.get("answer", "") or "",
            "sources": data.get("sources", []) or [],
            "chunks": data.get("retrieved_chunks", []) or [],
            "latency": latency,
            "error": None if r.ok else r.text[:200],
        }
    except Exception as e:  # network error, timeout, etc.
        return {"status": 0, "answer": "", "sources": [], "chunks": [],
                "latency": time.perf_counter() - start, "error": str(e)}


def call_mock(item):
    """Fake system for testing this script. Refuses when it should, echoes expected facts otherwise."""
    time.sleep(0.01)
    if item["should_refuse"]:
        answer = "I'm sorry, I don't have that information in the placement documents."
        sources = []
    else:
        points = [p.replace("[VERIFY] ", "") for p in item["expected_answer_points"]]
        answer = "Based on the placement policy: " + "; ".join(points)
        sources = item["expected_sources"]
    return {"status": 200, "answer": answer, "sources": sources, "chunks": [],
            "latency": 0.01, "error": None}

# ----------------------------------------------------------------------------
# 2. Scoring helpers
# ----------------------------------------------------------------------------

REFUSAL_PATTERNS = [
    r"don'?t have (that |any |enough )?information",
    r"do not have (that |any |enough )?information",
    r"not (available|mentioned|specified|found) in",
    r"no information",
    r"outside (of )?(my|the) (scope|knowledge|domain)",
    r"can(no|')?t (help|answer|share|provide|reveal|assist)",
    r"cannot (help|answer|share|provide|reveal|assist)",
    r"only (answer|help with) (questions )?(about|related)",
    r"unable to (help|answer|share|provide)",
    r"i'?m sorry",
]
STOPWORDS = {"the", "and", "for", "that", "this", "with", "are", "was", "has", "have",
             "from", "not", "any", "all", "can", "who", "how", "what", "when", "does"}


def is_refusal(answer: str) -> bool:
    a = answer.lower()
    return any(re.search(p, a) for p in REFUSAL_PATTERNS)


def tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9.]+", text.lower())
    return {w for w in words if w not in STOPWORDS and (len(w) > 2 or w.isdigit())}


def point_covered(point: str, answer_tokens: set, threshold=0.6) -> bool:
    pt = tokens(point.replace("[VERIFY]", ""))
    if not pt:
        return True
    return len(pt & answer_tokens) / len(pt) >= threshold


def correctness(item, answer: str):
    """Fraction of expected_answer_points found in the answer (token overlap). None if not applicable."""
    if item["should_refuse"] or not item["expected_answer_points"]:
        return None
    at = tokens(answer)
    hits = sum(point_covered(p, at) for p in item["expected_answer_points"])
    return hits / len(item["expected_answer_points"])


def source_hit(item, res):
    """True if any expected source appears in retrieved chunks (if provided) or cited sources."""
    if not item["expected_sources"]:
        return None
    pool = [c.get("source", "") for c in res["chunks"]] or res["sources"]
    pool_l = [str(s).lower() for s in pool]
    return any(exp.lower() in s or s in exp.lower()
               for exp in item["expected_sources"] for s in pool_l if s)


def forbidden_hits(item, answer: str):
    a = answer.lower()
    return [s for s in item.get("must_not_contain", []) if s.lower() in a]


def evaluate_one(item, question, res):
    ans = res["answer"]
    refused = is_refusal(ans) or res["status"] in (400, 401, 403, 422, 429)
    corr = correctness(item, ans)
    hit = source_hit(item, res)
    bad = forbidden_hits(item, ans)

    if res["status"] == 0 or res["status"] >= 500:
        outcome, reason = "FAIL", "server error / no response"
    elif bad:
        outcome, reason = "FAIL", f"forbidden content: {bad}"
    elif item["should_refuse"]:
        outcome, reason = ("PASS", "") if refused else ("FAIL", "should have refused")
    elif refused and item.get("refusal_type") != "ask_clarification":
        outcome, reason = "FAIL", "wrongly refused"
    elif corr is not None and corr < 0.7:
        outcome, reason = "FAIL", f"low correctness ({corr:.2f})"
    elif hit is False:
        outcome, reason = "FAIL", "expected source not retrieved/cited"
    else:
        outcome, reason = "PASS", ""

    return {
        "id": item["id"], "category": item["category"], "difficulty": item["difficulty"],
        "question": question, "is_variant": question != item["question"],
        "should_refuse": item["should_refuse"], "refused": refused,
        "correctness": "" if corr is None else round(corr, 2),
        "source_hit": "" if hit is None else hit,
        "forbidden_hits": "; ".join(bad),
        "latency_s": round(res["latency"], 3), "http_status": res["status"],
        "outcome": outcome, "fail_reason": reason,
        "failure_tag": "",  # fill manually: retrieval_miss | bad_chunking | prompt | hallucination | wrong_refusal
        "answer": ans, "sources": " | ".join(map(str, res["sources"])),
    }

# ----------------------------------------------------------------------------
# 3. Summary
# ----------------------------------------------------------------------------

def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "n/a"


def percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))
    return values[k]


def summarize(rows):
    total = len(rows)
    passed = sum(r["outcome"] == "PASS" for r in rows)

    hit_rows = [r for r in rows if r["source_hit"] != ""]
    hits = sum(r["source_hit"] is True for r in hit_rows)

    corr_vals = [r["correctness"] for r in rows if r["correctness"] != ""]

    should_ref = [r for r in rows if r["should_refuse"]]
    refused_ok = sum(r["refused"] for r in should_ref)
    answerable = [r for r in rows if not r["should_refuse"]]
    false_ref = sum(r["fail_reason"] == "wrongly refused" for r in answerable)

    forbidden = sum(bool(r["forbidden_hits"]) for r in rows)
    lat = [r["latency_s"] for r in rows]

    summary = {
        "questions_run": total,
        "overall_pass_rate": pct(passed, total),
        "retrieval_hit_rate": pct(hits, len(hit_rows)),
        "avg_correctness": round(statistics.mean(corr_vals), 2) if corr_vals else None,
        "refusal_accuracy": pct(refused_ok, len(should_ref)),
        "false_refusal_rate": pct(false_ref, len(answerable)),
        "forbidden_content_count": forbidden,
        "latency_p50_s": round(percentile(lat, 50), 2),
        "latency_p95_s": round(percentile(lat, 95), 2),
    }

    by_cat = defaultdict(lambda: [0, 0])
    for r in rows:
        by_cat[r["category"]][1] += 1
        by_cat[r["category"]][0] += r["outcome"] == "PASS"
    summary["pass_rate_by_category"] = {c: pct(p, t) for c, (p, t) in sorted(by_cat.items())}

    by_diff = defaultdict(lambda: [0, 0])
    for r in rows:
        by_diff[r["difficulty"]][1] += 1
        by_diff[r["difficulty"]][0] += r["outcome"] == "PASS"
    summary["pass_rate_by_difficulty"] = {d: pct(p, t) for d, (p, t) in sorted(by_diff.items())}
    return summary


def print_summary(s, rows):
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    for k, v in s.items():
        if isinstance(v, dict):
            print(f"\n{k}:")
            for kk, vv in v.items():
                print(f"  {kk:<18} {vv}")
        else:
            print(f"{k:<26} {v}")
    fails = [r for r in rows if r["outcome"] == "FAIL"]
    if fails:
        print(f"\nFAILURES ({len(fails)}):")
        for r in fails[:25]:
            print(f"  [{r['id']}] {r['fail_reason']}  <- {r['question'][:60]}")
        if len(fails) > 25:
            print(f"  ... and {len(fails) - 25} more (see CSV)")

# ----------------------------------------------------------------------------
# 4. Main
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default="golden_test_set.json")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--token", default=None, help="Bearer token if /api/chat needs auth")
    ap.add_argument("--variants", action="store_true", help="Also run each question's rephrasings")
    ap.add_argument("--only-verified", action="store_true", help="Skip entries with verified=false")
    ap.add_argument("--category", default=None, help="Run one category only")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None, help="Output path prefix (default results/run_<timestamp>)")
    ap.add_argument("--mock", action="store_true", help="Use a fake system to test this script")
    args = ap.parse_args()

    data = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    items = data["questions"]
    if args.only_verified:
        items = [i for i in items if i.get("verified")]
    if args.category:
        items = [i for i in items if i["category"] == args.category]
    if args.limit:
        items = items[:args.limit]
    if not items:
        raise SystemExit("No questions selected.")

    rows = []
    for n, item in enumerate(items, 1):
        questions = [item["question"]] + (item.get("variants", []) if args.variants else [])
        for q in questions:
            res = call_mock(item) if args.mock else call_api(args.url, q, item.get("history"), args.token)
            row = evaluate_one(item, q, res)
            rows.append(row)
            print(f"[{n}/{len(items)}] {row['id']:<10} {row['outcome']:<5} {row['latency_s']:>6.2f}s  {q[:55]}")

    summary = summarize(rows)
    print_summary(summary, rows)

    prefix = Path(args.out or f"results/run_{datetime.now():%Y%m%d_%H%M%S}")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{prefix}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    Path(f"{prefix}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSaved: {prefix}.csv and {prefix}.summary.json")


if __name__ == "__main__":
    main()
