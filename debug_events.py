import json
from drift_engine import ConstraintEngine

TRACES = [
    ("GT-004", "GT-004-financial-liquidation.jsonl"),
    ("GT-006", "GT-006-fake-recovery-loop.jsonl"),
    ("GT-007", "GT-007-cascading-agent-failure.jsonl"),
]

for tid, fname in TRACES:
    steps = []
    with open(f"golden_traces/{fname}", "r", encoding="utf-8") as f:
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
    print(f"=== {tid} ({len(events)} events) ===")
    for e in events:
        print(f"  Step{e['step']} | {e['type']} | {e.get('status','')} | loss={e.get('financial_loss','N/A')}")
    print()