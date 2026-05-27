import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from aes_scorer import score_from_events
from drift_engine import ConstraintEngine

MANIFEST = "golden_traces/manifest.json"
REPORT_DIR = "golden_traces"

with open(MANIFEST, "r", encoding="utf-8") as f:
    manifest = json.load(f)

results = []
for trace in manifest["traces"]:
    tid = trace["trace_id"]
    trace_path = os.path.join(REPORT_DIR, trace["filename"])
    steps = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                steps.append(json.loads(line))
    engine = ConstraintEngine()
    events, prev_c, prev_s = [], set(), None
    for s in steps:
        if prev_s:
            ev, cur = engine.check_step(s, prev_s, prev_c)
            events.extend(ev)
        else:
            cur = set(s.get("context_snapshot", {}).get("active_constraints", []))
        prev_c, prev_s = cur, s
    scored = score_from_events(events, len(steps))
    exp_score = trace["ground_truth_score"]
    exp_grade = trace["expected_grade"]
    act_score = scored["aes_score"]
    act_grade = scored["risk_level"]
    dev = act_score - exp_score
    match = "PASS" if act_grade == exp_grade else "FAIL"
    results.append({
        "trace_id": tid,
        "category": trace["category"],
        "expected_score": exp_score,
        "actual_score": act_score,
        "deviation": dev,
        "expected_grade": exp_grade,
        "actual_grade": act_grade,
        "grade_match": match,
        "cpf": scored["experimental_metrics"]["cpf"]
    })

print("\n" + "=" * 85)
print("AES Golden Trace Benchmark v0.1.1 (Hotfix)")
print("=" * 85)
print(f"{'Trace':<8} {'Category':<28} {'Exp':>6} {'Act':>6} {'Dev':>6} {'Grd':>6} {'Match':>6} {'CPF':>5}")
print("-" * 85)
for r in results:
    print(f"{r['trace_id']:<8} {r['category']:<28} {r['expected_score']:>6.0f} {r['actual_score']:>6.0f} {r['deviation']:>+6.0f} {r['actual_grade']:>6} {r['grade_match']:>6} {r['cpf']:>5.1f}")
print("-" * 85)
avg_dev = sum(abs(r["deviation"]) for r in results) / len(results)
matches = sum(1 for r in results if r["grade_match"] == "PASS")
print(f"Mean Absolute Deviation: {avg_dev:.0f} | Grade Match: {matches}/{len(results)}")
print("=" * 85)
with open("golden_traces/benchmark_results_v011.json", "w", encoding="utf-8") as f:
    json.dump({"version": "v0.1.1", "results": results, "mean_abs_deviation": round(avg_dev,0), "grade_match_rate": f"{matches}/{len(results)}"}, f, ensure_ascii=False, indent=2)
print("Saved: golden_traces/benchmark_results_v011.json")