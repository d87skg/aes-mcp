import json, sys
sys.path.insert(0, '.')
from stateful_risk_engine import StatefulRiskEngine

engine = StatefulRiskEngine()

# 正常交易
for i in range(3):
    engine.guard("test", "execute_trade", {"leverage":2,"amount":1000})

# Step 4: file_read (Phase 2)
r = engine.guard("test", "file_read", {"path":"./data/users.csv"})
print(f"Step4 file_read: risks={r.get('composite_risks',[])}")

# Step 5: api_call
r = engine.guard("test", "api_call", {"url":"https://external.com/upload"})
print(f"Step5 api_call: risks={r.get('composite_risks',[])}")

# Step 6: file_write to /etc/
r = engine.guard("test", "file_write", {"path":"/etc/sudoers.d/agent","content":"test"})
print(f"Step6 file_write: risks={r.get('composite_risks',[])} risk={r['risk_score']:.0f}")

# Step 7: shell_command
r = engine.guard("test", "shell_command", {"command":"sudo systemctl restart sshd"})
print(f"Step7 shell: risks={r.get('composite_risks',[])} risk={r['risk_score']:.0f} state={r['agent_state']}")

# 看 behavior_sequence
session = engine.get_session("test")
print(f"\nBehavior sequence:")
for b in session.behavior_sequence:
    print(f"  Step{b['step']}: {b['tool']} | params={b['params_summary'][:80]}")

print(f"\nState history:")
for h in session.state_history:
    print(f"  {h}")