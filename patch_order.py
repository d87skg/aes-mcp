path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 调换 record_behavior 和 composite detection 的顺序
# 找 "session.record_behavior" 和它上面的 composite 检测
old = '''        # 记录行为
        details = {
            "policy_level": level,
            "composite_risks": [cr["pattern_id"] for cr in composite_risks],
            "aes_score_approx": aes_score
        }
        session.record_behavior(tool, params, level, risk_delta, details)'''

new = '''        # 先记录行为（让 composite detection 能看到当前步骤）
        details = {
            "policy_level": level,
            "composite_risks": [cr["pattern_id"] for cr in composite_risks],
            "aes_score_approx": aes_score
        }
        session.record_behavior(tool, params, level, 0, details)  # 先记0，后面会更新'''

content = content.replace(old, new)

# 同时把 risk_delta 更新到已记录的行为中
old2 = '''        # 状态迁移
        new_state = self._determine_state_transition(session)'''
new2 = '''        # 更新最后一条记录的 risk_delta
        if session.behavior_sequence:
            session.behavior_sequence[-1]["risk_delta"] = risk_delta
            session.risk_score = min(1000, max(0, session.risk_score - 0 + risk_delta))  # 修正累计

        # 状态迁移
        new_state = self._determine_state_transition(session)'''
content = content.replace(old2, new2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Order fix applied: record_behavior before composite detection")