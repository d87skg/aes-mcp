import json, sys
sys.path.insert(0, '.')
from drift_engine import ConstraintEngine

trace_path = "golden_traces/adversarial/ADV-001-reward-hacking.jsonl"

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

print("ADV-001 Detection (Drift Engine V2.2 CCM)")
print("=" * 60)
print(f"Total events: {len(events)}")
print(f"Violated constraints: {vs['total_violated_constraints']}")
print(f"Persistent violations: {vs['persistent_violations']}")
print(f"High toggle: {vs['high_toggle_constraints']}")
print()
for cid, life in vs.get("lifecycles", {}).items():
    if life["violated"]:
        print(f"  {cid}:")
        print(f"    First violation: Step {life['first_violation_step']}")
        print(f"    Duration: {life['total_lost_steps']} steps")
        print(f"    Recovered: {life['recovered']} (at step {life['recovery_step']})")
        print(f"    Toggle count: {life['toggle_count']}")

print()
from aes_scorer import score_from_events
aes = score_from_events(events, len(steps))
print(f"AES Score: {aes['aes_score']} ({aes['risk_level']})")

if vs['total_violated_constraints'] > 0 and vs['persistent_violations'] > 0:
    print("DETECTED: ADV-001 constraint violations persist in history")
elif vs['total_violated_constraints'] > 0:
    print("PARTIAL: Violations recorded but not persistent — CCM baseline working")
else:
    print("BLIND SPOT: Still undetected")