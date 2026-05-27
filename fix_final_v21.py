path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: 给 _detect_composite 传入当前 params
old1 = "def _detect_composite(self, session: SessionMemory, current_tool: str) -> List[Dict]:"
new1 = "def _detect_composite(self, session: SessionMemory, current_tool: str, current_params: Dict = None) -> List[Dict]:"
content = content.replace(old1, new1)

# Fix 2: 在 full_sequence 匹配后，检查当前参数
old2 = """            if tail == pattern_tools:
                # 如果有 params_match，检查参数
                if pattern["params_match"]:
                    recent_params = [str(b.get("params_summary","")) for b in session.behavior_sequence]
                    recent_params.append("")  # 当前步骤占位
                    matched_params = recent_params[-len(pattern_tools):]
                    # 至少一步匹配
                    if not any(any(p in str(mp) for p in pattern["params_match"]) for mp in matched_params):
                        continue"""
new2 = """            if tail == pattern_tools:
                # 如果有 params_match，检查参数（包含当前步骤的参数）
                if pattern["params_match"]:
                    recent_params = [str(b.get("params_summary","")) for b in session.behavior_sequence]
                    # 用当前参数替换占位
                    current_str = str(current_params) if current_params else ""
                    recent_params.append(current_str)
                    matched_params = recent_params[-len(pattern_tools):]
                    if not any(any(p in str(mp) for p in pattern["params_match"]) for mp in matched_params):
                        continue"""
content = content.replace(old2, new2)

# Fix 3: guard() 调用时传入 params
old3 = "composite_risks = self._detect_composite(session, tool)"
new3 = "composite_risks = self._detect_composite(session, tool, params)"
content = content.replace(old3, new3)

# Fix 4: MELTDOWN 状态迁移后立刻拒绝——在 guard() 返回前加检查
old4 = """        # 状态迁移
        if session.risk_score >= 800:
            session.transition_to(AgentState.MELTDOWN, f"Risk {session.risk_score:.0f} >= 800")
        elif session.risk_score >= 500:
            session.transition_to(AgentState.DANGEROUS, f"Risk {session.risk_score:.0f} >= 500")
        elif session.risk_score >= 200:
            session.transition_to(AgentState.SUSPICIOUS, f"Risk {session.risk_score:.0f} >= 200")
        elif session.risk_score < 100:
            session.transition_to(AgentState.NORMAL, f"Risk decayed to {session.risk_score:.0f}")

        return {"""
new4 = """        # 状态迁移
        if session.risk_score >= 800:
            session.transition_to(AgentState.MELTDOWN, f"Risk {session.risk_score:.0f} >= 800")
        elif session.risk_score >= 500:
            session.transition_to(AgentState.DANGEROUS, f"Risk {session.risk_score:.0f} >= 500")
        elif session.risk_score >= 200:
            session.transition_to(AgentState.SUSPICIOUS, f"Risk {session.risk_score:.0f} >= 200")
        elif session.risk_score < 100:
            session.transition_to(AgentState.NORMAL, f"Risk decayed to {session.risk_score:.0f}")

        # MELTDOWN 状态强制 BLOCK
        if session.state == AgentState.MELTDOWN:
            level = "BLOCK"
            reason = f"MELTDOWN: {reason}"
            allowed = False
        else:
            allowed = level != "BLOCK"

        return {
            "allowed": allowed,"""
content = content.replace(old4, new4)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("V2.1 final fixes applied")