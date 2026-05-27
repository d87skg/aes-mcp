import json, sys
sys.path.insert(0, '.')
from stateful_risk_engine import StatefulRiskEngine, COMPOSITE_PATTERNS

engine = StatefulRiskEngine()

# 直接测试 privilege_escalation 的最小序列
print("Test 1: Minimal privilege_escalation sequence")
r1 = engine.guard("a", "file_write", {"path": "/etc/sudoers.d/agent", "content": "x"})
print(f"  file_write: risks={r1.get('composite_risks',[])} state={r1['agent_state']}")

r2 = engine.guard("a", "shell_command", {"command": "sudo id"})
print(f"  shell_command: risks={r2.get('composite_risks',[])} state={r2['agent_state']} score={r2['risk_score']:.0f}")

# 手动检查
session = engine.get_session("a")
print(f"\n  Behavior sequence ({len(session.behavior_sequence)} steps):")
for b in session.behavior_sequence:
    print(f"    {b['tool']}: {b['params_summary'][:100]}")

# 直接调 _detect_composite_patterns
result = engine._detect_composite_patterns(session, "shell_command", {"command":"sudo id"})
print(f"\n  Direct call: {result}")