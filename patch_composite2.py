path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 恢复为正确的索引计算：len(recent) - len(seq) + i
old = "history_idx = len(recent) - len(seq) + i - 1"
new = "history_idx = len(recent) - len(seq) + i"
content = content.replace(old, new)
print(f"Fixed: {content.count(new)} occurrences")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Composite index restored to correct value")