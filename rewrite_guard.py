path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 guard() 方法，替换从 composite_risks 到状态迁移的整个逻辑块
old_start = "        # 组合行为检测\n        composite_risks = self._detect_composite_patterns(session, tool, params)"
old_end = "        # 更新最后一条记录的 risk_delta"

# 用新的正确顺序替换
new_logic = """        # 先记录行为（让 composite detection 能看到当前步骤）
        details = {
            "policy_level": level,
            "composite_risks": [],
            "aes_score_approx": aes_score
        }
        session.record_behavior(tool, params, level, 0, details)

        # 组合行为检测（在记录之后，能看到当前步骤）
        composite_risks = self._detect_composite_patterns(session, tool, params)

        # 计算风险增量
        risk_delta = 0
        if level == "BLOCK":
            risk_delta = 150
        elif level == "RESTRICT":
            risk_delta = 80
        elif level == "WARN":
            risk_delta = 30
        elif level == "ALLOW":
            risk_delta = -5

        for cr in composite_risks:
            risk_delta += cr["risk_delta"]
            desc = cr["description"]
            if cr["auto_meltdown"]:
                level = "BLOCK"
                actions.append("deny_execution")
                reason = f"Composite pattern detected: {desc}"
                session.transition(AgentState.MELTDOWN, f"Auto-meltdown: {desc}")"""

# 找到并替换
if old_start in content and old_end in content:
    start_idx = content.index(old_start)
    end_idx = content.index(old_end)
    content = content[:start_idx] + new_logic + "\n\n        " + content[end_idx:]
    print("Guard method rewritten with correct order")
else:
    print("Pattern not found - checking positions")
    print(f"old_start found: {old_start in content}")
    print(f"old_end found: {old_end in content}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Rewrite complete")