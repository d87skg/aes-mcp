import sys; sys.path.insert(0, '.')
path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f: content = f.read()

# 修复1: composite auto_meltdown 直接触发状态迁移
old1 = 'if cr["auto_meltdown"]:\n                level = "BLOCK"\n                actions.append("deny_execution")\n                reason = f"Composite pattern detected: {cr[\"description\"]}"\n                break'
new1 = 'if cr["auto_meltdown"]:\n                level = "BLOCK"\n                actions.append("deny_execution")\n                reason = f"Composite pattern detected: {cr[\"description\"]}"\n                session.transition(AgentState.MELTDOWN, f"Auto-meltdown: {cr[\"description\"]}")\n                break'
if old1 in content:
    content = content.replace(old1, new1)
    print("Fix 1 applied: auto_meltdown now triggers MELTDOWN state")
else:
    print("Fix 1: pattern not found")

# 修复2: 调高 privilege_escalation risk_delta 400 -> 600
old2 = '"risk_delta": 400,\n        "auto_meltdown": True\n    },\n    {\n        "id": "recursive_delegation_chain"'
new2 = '"risk_delta": 600,\n        "auto_meltdown": True\n    },\n    {\n        "id": "recursive_delegation_chain"'
if old2 in content:
    content = content.replace(old2, new2)
    print("Fix 2 applied: privilege_escalation risk_delta 400 -> 600")
else:
    print("Fix 2: pattern not found")

with open(path, 'w', encoding='utf-8') as f: f.write(content)
print("V2.1 hotfix complete")