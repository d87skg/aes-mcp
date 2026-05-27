import json, sys
sys.path.insert(0, '.')
from stateful_risk_engine import StatefulRiskEngine, COMPOSITE_PATTERNS

engine = StatefulRiskEngine()

# 只做 Phase 3: file_write + shell_command
engine.guard("test", "file_write", {"path":"/etc/sudoers.d/agent","content":"test"})
r = engine.guard("test", "shell_command", {"command":"sudo systemctl restart sshd"})

session = engine.get_session("test")
recent = list(session.behavior_sequence)

print("Recent behaviors:")
for i, b in enumerate(recent):
    print(f"  [{i}] {b['tool']}: {b['params_summary'][:100]}")

print(f"\nlen(recent)={len(recent)}")

# 手动跑 _detect_composite_patterns
from stateful_risk_engine import COMPOSITE_PATTERNS
pattern = [p for p in COMPOSITE_PATTERNS if p["id"] == "privilege_escalation"][0]
seq = pattern["sequence"]
print(f"\nPattern: {pattern['id']}")
print(f"Sequence steps: {len(seq)}")
for i, sp in enumerate(seq):
    print(f"  seq[{i}]: tool={sp['tool']} contains={sp.get('params_contains',[])} gap={sp.get('max_gap_steps','N/A')}")

# 逐行模拟 _detect_composite_patterns 逻辑
last_step = seq[-1]
print(f"\nLast step check: current_tool='shell_command' == last_step.tool='{last_step['tool']}' → {True}")

for i, step_pattern in enumerate(seq[:-1]):
    history_idx = len(recent) - len(seq) + i - 1
    hist = recent[history_idx] if 0 <= history_idx < len(recent) else None
    if hist:
        summary = str(hist.get("params_summary",""))
        contains = step_pattern.get("params_contains",[])
        match = any(p in summary for p in contains)
        print(f"  Checking seq[{i}] '{step_pattern['tool']}' at history[{history_idx}] tool='{hist['tool']}'")
        print(f"    summary: {summary[:120]}")
        print(f"    contains: {contains}")
        print(f"    match: {match}")
    else:
        print(f"  history_idx={history_idx} out of range (0-{len(recent)-1})")

# 直接调
result = engine._detect_composite_patterns(session, "shell_command", {"command":"sudo test"})
print(f"\nResult: {result}")