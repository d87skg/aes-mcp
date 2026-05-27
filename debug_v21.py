import sys; sys.path.insert(0, '.')
path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找 auto_meltdown 相关行
for i, line in enumerate(lines):
    if 'auto_meltdown' in line and 'composite' not in line and 'cr[' in line:
        start = max(0, i-1)
        end = min(len(lines), i+5)
        print(f"--- Lines {start+1}-{end} ---")
        for j in range(start, end):
            print(f"{j+1}: {lines[j].rstrip()}")
        print()