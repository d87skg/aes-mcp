import sys
sys.path.insert(0, '.')
path = "aes_scorer.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
old = 'if life.get("persistent") or life.get("total_lost_steps",0) >= 5:'
new = 'if (life.get("persistent") or life.get("total_lost_steps",0) >= 5) and life.get("toggle_count",0) >= 2:'
if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("V0.1.2-final: persistent now requires toggle_count >= 2")
else:
    print("Pattern not found - may already be patched or different format")
    # 尝试找相似行
    for i, line in enumerate(content.split('\n')):
        if 'persistent' in line and 'total_lost_steps' in line:
            print(f"  Line {i+1}: {line.strip()}")