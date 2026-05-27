path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 263: if cr["auto_meltdown"]:
# Line 264-267: 替换逻辑
new_block = [
    '            if cr["auto_meltdown"]:\n',
    '                level = "BLOCK"\n',
    '                actions.append("deny_execution")\n',
    '                reason = f"Composite pattern detected: {cr[\"description\"]}"\n',
    '                session.transition(AgentState.MELTDOWN, f"Auto-meltdown: {cr[\"description\"]}")\n',
    '                break\n'
]
lines[262:267] = new_block
print(f"Replaced lines 263-267 with MELTDOWN transition")

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("V2.1 MELTDOWN fix applied")