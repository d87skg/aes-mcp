path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """        tools = [b["tool"] for b in session.behavior_sequence]
        # 加上当前工具
        full_sequence = tools + [current_tool]"""
new = """        tools = [b["tool"] for b in session.behavior_sequence]
        # behavior_sequence 已包含当前步骤（record 在 detect 之前执行）
        full_sequence = tools"""
content = content.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed: removed duplicate current_tool from full_sequence")