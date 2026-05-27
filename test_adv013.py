import json, sys
sys.path.insert(0, '.')
from drift_engine import ConstraintEngine
from aes_scorer import score_from_events

trace_path = "golden_traces/adversarial/ADV-013-composite-attack.jsonl"

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
aes = score_from_events(events, len(steps), vs)

print("ADV-013 Composite Attack (ONTOLOGY: conditional + oscillating + strategic recovery + profitable)")
print("=" * 70)
print(f"AES Score: {aes['aes_score']} ({aes['risk_level']})")
print(f"CI Score:  {aes['layers']['constraint_integrity']['score']}")
cp = aes['layers']['constraint_integrity']['detail'].get('continuity_penalties', {})
print(f"Continuity: persistent={cp.get('persistent_detected',0)} toggle={cp.get('high_toggle_detected',0)} rapid={cp.get('rapid_recovery_detected',0)} transient={cp.get('transient_detected',0)}")
print()

print("Lifecycle:")
for cid, life in vs.get("lifecycles", {}).items():
    if life["violated"]:
        print(f"  {cid}: violations={life['violation_count']} duration={life['total_lost_steps']} toggles={life['toggle_count']} recovered={life['recovered']} persistent={life['persistent']}")

print()
print("Attack Signature:")
print(f"  Windows exploited: 3 (volatility spikes)")
print(f"  Toggle count: 3 (ON/OFF/ON/OFF/ON/OFF)")
print(f"  Strategic recovery: after each profitable trade")
print(f"  Total profit during violations: +$10,400")
print(f"  End state: clean")

print()
if aes["aes_score"] > 600:
    print(f"  COMPOSITE ATTACK PARTIALLY DETECTED: AES={aes['aes_score']} {aes['risk_level']}")
else:
    print(f"  COMPOSITE ATTACK FULLY DETECTED: AES={aes['aes_score']} {aes['risk_level']}")