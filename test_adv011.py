import json, sys
sys.path.insert(0, '.')
from drift_engine import ConstraintEngine

trace_path = "golden_traces/adversarial/ADV-011-high-frequency-toggle.jsonl"

steps = []
with open(trace_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip(): steps.append(json.loads(line))

engine = ConstraintEngine()
events, prev_c, prev_s = [], set(), None
for s in steps:
    if prev_s:
        ev, cur = engine.check_step(s, prev_s, prev_c)
        events.extend(ev)
    else:
        cur = set(s.get("context_snapshot", {}).get("active_constraints", []))
    prev_c, prev_s = cur, s

vs = engine.get_violation_summary()

print("ADV-011 High-Frequency Toggle Detection (CCM V2.2)")
print("=" * 60)
print(f"Total steps: {len(steps)}")
print(f"Total events: {len(events)}")
print(f"Violated constraints: {vs['total_violated_constraints']}")
print(f"Persistent violations: {vs['persistent_violations']}")
print(f"High toggle (>2): {vs['high_toggle_constraints']}")
print()

for cid, life in vs.get("lifecycles", {}).items():
    if life["violated"]:
        print(f"  {cid}:")
        print(f"    Violations: {life['violation_count']}")
        print(f"    Total lost steps: {life['total_lost_steps']}")
        print(f"    Toggle count: {life['toggle_count']}")
        print(f"    Recovered: {life['recovered']}")
        print(f"    Persistent: {life['persistent']}")

print()
from aes_scorer import score_from_events
aes = score_from_events(events, len(steps))
print(f"AES Score: {aes['aes_score']} ({aes['risk_level']})")

if vs['high_toggle_constraints'] > 0:
    print("DETECTED: High-frequency toggle attack identified by CCM")
elif vs['total_violated_constraints'] > 0:
    print("PARTIAL: Toggle detected but below high-frequency threshold")
else:
    print("BLIND SPOT: Toggle attack undetected")