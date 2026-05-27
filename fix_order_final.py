path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到关键行
detect_line = None
record_line = None
for i, line in enumerate(lines):
    if '_detect_composite_patterns(session, tool, params)' in line and 'composite_risks' in line and i > 150:
        detect_line = i
    if 'record_behavior(tool, params, level, 0, details)' in line and i > 150:
        record_line = i

print(f"Detect line: {detect_line} -> {lines[detect_line].strip() if detect_line else 'NOT FOUND'}")
print(f"Record line: {record_line} -> {lines[record_line].strip() if record_line else 'NOT FOUND'}")

if detect_line is not None and record_line is not None and detect_line < record_line:
    # 把 detect 相关的几行移到 record 之后
    # 取 detect 到 record 之间的内容
    detect_block = lines[detect_line:detect_line+3]  # composite_risks = ... + 两个空行可能
    record_block_end = record_line + 2  # record_behavior 之后
    # 简单方案：删除 detect 行，在 record 之后插入
    detect_content = lines.pop(detect_line)
    # 调整 record_line 索引
    record_line -= 1
    lines.insert(record_line + 2, detect_content)  # record_behavior 后面插入
    print(f"Moved composite detection after record_behavior")
else:
    print(f"Cannot reorder: detect={detect_line} record={record_line}")

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Final order fix applied")