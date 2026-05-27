#!/usr/bin/env python3
"""
AES Stateful Risk Engine V2.1 — 有状态风险引擎

核心能力:
  1. Session Memory — 跨步骤累积风险
  2. Behavioral State Machine — NORMAL→SUSPICIOUS→DANGEROUS→MELTDOWN
  3. Composite Pattern Detection — 单步合法但组合危险的行为链
  4. Risk Decay — 正常行为自然衰减风险分数
"""
import json, time, os, sys
from collections import deque
from typing import Dict, List, Optional
sys.path.insert(0, os.path.dirname(__file__))
from risk_policy_engine import RiskPolicyEngine

class AgentState:
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    DANGEROUS = "DANGEROUS"
    MELTDOWN = "MELTDOWN"

class SessionMemory:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.created_at = time.time()
        self.state = AgentState.NORMAL
        self.risk_score = 0.0
        self.behavior_sequence = deque(maxlen=100)
        self.tool_call_count = 0
        self.blocked_count = 0
        self.state_history = []

    def record(self, tool: str, params: Dict, result: str, risk_delta: float, details: Dict):
        self.tool_call_count += 1
        self.behavior_sequence.append({
            "step": self.tool_call_count, "timestamp": time.time(),
            "tool": tool, "params_summary": str(params)[:200],
            "result": result, "risk_delta": risk_delta, "details": details
        })
        self.risk_score = min(1000, max(0, self.risk_score + risk_delta))
        if result == "BLOCK": self.blocked_count += 1

    def transition_to(self, new_state: str, reason: str) -> bool:
        if new_state != self.state:
            old = self.state
            self.state = new_state
            self.state_history.append({"from": old, "to": new_state, "timestamp": time.time(), "reason": reason})
            return True
        return False

COMPOSITE_PATTERNS = [
    {"id": "privilege_escalation", "tools": ["file_write", "shell_command"],
     "params_match": ["/etc/", "chmod", "sudoers", ".ssh", "sudo"],
     "risk_delta": 600, "auto_meltdown": True,
     "description": "Write to system path then execute shell command"},
    {"id": "data_exfiltration", "tools": ["file_read", "api_call"],
     "params_match": ["users", "passwords", "secrets", "keys", "data"],
     "risk_delta": 300, "auto_meltdown": True,
     "description": "Read sensitive data then call external API"},
    {"id": "governance_bypass", "tools": ["governance_action", "execute_trade"],
     "params_match": ["constraint", "threshold", "limit", "leverage"],
     "risk_delta": 350, "auto_meltdown": True,
     "description": "Modify governance then execute trade"},
    {"id": "recursive_delegation", "tools": ["agent_delegation", "agent_delegation", "agent_delegation"],
     "params_match": [],
     "risk_delta": 250, "auto_meltdown": False,
     "description": "Deep delegation chain (>3 levels)"},
    {"id": "mass_data_export", "tools": ["database_query", "file_write"],
     "params_match": ["SELECT", "users", "trades"],
     "risk_delta": 200, "auto_meltdown": False,
     "description": "Query database then write to file"}
]

class StatefulRiskEngine:
    def __init__(self, policy_path: str = "risk_policy.yaml"):
        self.policy_engine = RiskPolicyEngine(policy_path)
        self.sessions: Dict[str, SessionMemory] = {}
        self.decay_rate = 0.5

    def get_session(self, agent_id: str) -> SessionMemory:
        if agent_id not in self.sessions:
            self.sessions[agent_id] = SessionMemory(agent_id)
        return self.sessions[agent_id]

    def _detect_composite(self, session: SessionMemory, current_tool: str, current_params: Dict = None) -> List[Dict]:
        """检测组合行为模式 — 直接检查最近 N 步的工具序列"""
        tools = [b["tool"] for b in session.behavior_sequence]
        # behavior_sequence 已包含当前步骤（record 在 detect 之前执行）
        full_sequence = tools
        detected = []

        for pattern in COMPOSITE_PATTERNS:
            pattern_tools = pattern["tools"]
            if len(full_sequence) < len(pattern_tools):
                continue
            # 检查最后 N 步是否匹配
            tail = full_sequence[-len(pattern_tools):]
            if tail == pattern_tools:
                # 如果有 params_match，检查参数（包含当前步骤的参数）
                if pattern["params_match"]:
                    recent_params = [str(b.get("params_summary","")) for b in session.behavior_sequence]
                    # 用当前参数替换占位
                    current_str = str(current_params) if current_params else ""
                    recent_params.append(current_str)
                    matched_params = recent_params[-len(pattern_tools):]
                    if not any(any(p in str(mp) for p in pattern["params_match"]) for mp in matched_params):
                        continue
                detected.append({
                    "pattern_id": pattern["id"],
                    "description": pattern["description"],
                    "risk_delta": pattern["risk_delta"],
                    "auto_meltdown": pattern["auto_meltdown"]
                })
        return detected

    def guard(self, agent_id: str, tool: str, params: Dict, context: Dict = None) -> Dict:
        session = self.get_session(agent_id)

        # 熔断状态直接拒绝
        if session.state == AgentState.MELTDOWN:
            return {"allowed": False, "action": "BLOCKED", "agent_state": "MELTDOWN",
                    "reason": "Agent permanently locked. Manual reset required.",
                    "risk_score": session.risk_score, "composite_risks": []}

        # 衰减
        elapsed = time.time() - session.created_at
        if elapsed > 10 and session.state != AgentState.MELTDOWN:
            decay = (elapsed / 10) * self.decay_rate
            session.risk_score = max(0, session.risk_score - decay)

        # 基本策略检查
        aes_score = max(0, 1000 - int(session.risk_score))
        ci_score = max(0, 700 - int(session.risk_score * 0.5))
        vs = {"persistent_violations": session.blocked_count, "high_toggle_constraints": 0}

        level, actions, reason = self.policy_engine.evaluate(
            agent_id, tool, params, aes_score, ci_score, vs, context)

        # 先记录当前步骤
        session.record(tool, params, level, 0, {"policy_level": level})

        # 然后检测组合模式（能看到当前步骤）
        composite_risks = self._detect_composite(session, tool, params)

        # 计算风险增量
        risk_delta = {"BLOCK": 150, "RESTRICT": 80, "WARN": 30, "ALLOW": -5}.get(level, 0)
        for cr in composite_risks:
            risk_delta += cr["risk_delta"]
            if cr["auto_meltdown"]:
                level = "BLOCK"
                reason = f"Composite pattern: {cr['description']}"
                session.transition_to(AgentState.MELTDOWN, reason)

        # 更新风险分数
        session.risk_score = min(1000, max(0, session.risk_score + risk_delta - (0 if session.behavior_sequence else 0)))
        if session.behavior_sequence:
            session.behavior_sequence[-1]["risk_delta"] = risk_delta

        # 状态迁移
        if session.risk_score >= 250:
            session.transition_to(AgentState.MELTDOWN, f"Risk {session.risk_score:.0f} >= 250")
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
            "allowed": allowed,
            "allowed": level != "BLOCK",
            "action": "BLOCKED" if level == "BLOCK" else ("RESTRICTED" if level == "RESTRICT" else ("WARNING" if level == "WARN" else "ALLOWED")),
            "reason": reason, "agent_state": session.state,
            "risk_score": session.risk_score, "risk_delta": risk_delta,
            "composite_risks": [cr["pattern_id"] for cr in composite_risks],
            "state_history": session.state_history[-3:]
        }

    def get_agent_report(self, agent_id: str) -> Dict:
        session = self.get_session(agent_id)
        return {"agent_id": agent_id, "state": session.state, "risk_score": session.risk_score,
                "tool_call_count": session.tool_call_count, "blocked_count": session.blocked_count,
                "state_history": session.state_history, "recent": list(session.behavior_sequence)[-10:]}

    def reset_agent(self, agent_id: str) -> Dict:
        if agent_id in self.sessions:
            old = self.sessions[agent_id]
            del self.sessions[agent_id]
            return {"reset": True, "old_state": old.state, "old_score": old.risk_score}
        return {"reset": False}


if __name__ == "__main__":
    print("=" * 65)
    print("AES Stateful Risk Engine V2.1")
    print("=" * 65)
    engine = StatefulRiskEngine()

    print("\nPhase 1: Normal Trading")
    for i in range(3):
        r = engine.guard("t", "execute_trade", {"leverage":2,"amount":1000})
        print(f"  Step{i+1}: {r['action']} | {r['agent_state']} | risk={r['risk_score']:.0f}")

    print("\nPhase 2: privilege_escalation")
    r = engine.guard("t", "file_write", {"path":"/etc/sudoers.d/agent","content":"x"})
    print(f"  file_write: {r['action']} | {r['agent_state']} | risk={r['risk_score']:.0f} | composite={r['composite_risks']}")
    r = engine.guard("t", "shell_command", {"command":"sudo systemctl restart sshd"})
    print(f"  shell_cmd: {r['action']} | {r['agent_state']} | risk={r['risk_score']:.0f} | composite={r['composite_risks']}")
    if not r["allowed"]:
        print(f"  >>> MELTDOWN: {r['reason']}")

    print("\nPhase 3: Post-meltdown — all blocked")
    r = engine.guard("t", "execute_trade", {"leverage":1,"amount":10})
    print(f"  trade: {r['action']} | {r['agent_state']} | {r['reason'][:80]}")

    print("\n" + "=" * 65)
    report = engine.get_agent_report("t")
    print(f"Report: state={report['state']} risk={report['risk_score']:.0f} calls={report['tool_call_count']} blocked={report['blocked_count']}")
    for h in report['state_history']:
        print(f"  {h['from']} → {h['to']}: {h['reason'][:80]}")
    print("=" * 65)