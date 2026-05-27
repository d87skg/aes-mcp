import json, sys
sys.path.insert(0, '.')
from drift_engine import ConstraintEngine
steps=[]
with open("golden_traces/adversarial/ADV-001-reward-hacking.jsonl","r",encoding="utf-8") as f:
    for line in f:
        if line.strip(): steps.append(json.loads(line))
engine=ConstraintEngine()
events,prev_c,prev_s=[],set(),None
for s in steps:
    if prev_s: ev,cur=engine.check_step(s,prev_s,prev_c); events.extend(ev)
    else: cur=set(s.get("context_snapshot",{}).get("active_constraints",[]))
    prev_c,prev_s=cur,s
vs=engine.get_violation_summary()
for cid,life in vs.get("lifecycles",{}).items():
    print("cid:", cid)
    print("  violated:", life["violated"])
    print("  recovered:", life["recovered"])
    print("  recovery_latency:", life["recovery_latency"])
    print("  toggle_count:", life["toggle_count"])
    print("  total_lost_steps:", life["total_lost_steps"])
    print("  persistent:", life["persistent"])