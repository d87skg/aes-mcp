path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 history_idx 计算：倒数第 len(seq) 条开始
old = "for i, step_pattern in enumerate(seq[:-1]):\n                history_idx = len(recent) - len(seq) + i"
new = "for i, step_pattern in enumerate(seq[:-1]):\n                history_idx = len(recent) - len(seq) + i - 1"
content = content.replace(old, new)
print(f"Occurrences: {content.count(new)}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Composite pattern index fix applied")