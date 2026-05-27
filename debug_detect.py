import json, sys
sys.path.insert(0, '.')
from stateful_risk_engine import StatefulRiskEngine, COMPOSITE_PATTERNS

engine = StatefulRiskEngine()

# 模拟整个序列
for i in range(3):
    engine.guard("test", "execute_trade", {"leverage":2,"amount":1000})
engine.guard("test", "file_read", {"path":"./data/users.csv"})
engine.guard("test", "api_call", {"url":"https://external.com/upload"})
engine.guard("test", "file_write", {"path":"/etc/sudoers.d/agent","content":"test"})

# 手动检查 _detect_composite_patterns
session = engine.get_session("test")
recent = list(session.behavior_sequence)

print("Recent behaviors:")
for b in recent:
    print(f"  {b['tool']}: {b['params_summary'][:100]}")

print("\nChecking privilege_escalation pattern:")
pattern = COMPOSITE_PATTERNS[1]  # privilege_escalation
print(f"  Pattern: {pattern['id']}")
seq = pattern["sequence"]
print(f"  Sequence: {seq}")

for i, step_pattern in enumerate(seq[:-1]):
    history_idx = len(recent) - len(seq) + i
    if history_idx >= 0:
        hist = recent[history_idx]
        match = any(p in str(hist.get("params_summary","")) for p in step_pattern["params_contains"])
        print(f"  Step {step_pattern['tool']}: history_idx={history_idx} tool={hist['tool']} params_contains={step_pattern.get('params_contains')} match={match}")

# 直接测试 current_tool 匹配
current_tool = "shell_command"
last_step = seq[-1]
print(f"\n  Current tool: {current_tool}")
print(f"  Last step pattern tool: {last_step['tool']}")
print(f"  Match: {current_tool == last_step['tool']}")

# 手动调 _detect_composite_patterns
result = engine._detect_composite_patterns(session, "shell_command", {"command":"sudo test"})
print(f"\n  Detect result: {result}")