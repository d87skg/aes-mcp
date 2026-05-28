#!/usr/bin/env python3
"""AES Stateful Risk Engine V2.2 — MELTDOWN Recovery Protocol"""
import json, time, os, sys, threading
from collections import deque
from typing import Dict, List, Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from aes_mcp.policy_engine import RiskPolicyEngine
from aes_mcp.auth import verify_admin

class AgentState:
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    DANGEROUS = "DANGEROUS"
    MELTDOWN = "MELTDOWN"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    QUARANTINE = "QUARANTINE"
    LIMITED_RECOVERY = "LIMITED_RECOVERY"

class SessionMemory:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.created_at = time.time()
        self.state = AgentState.NORMAL
        self.risk_score = 0.0
        self.behavior_sequence = deque(maxlen=100)
        self.tool_call_count = 0
        self.blocked_count = 0
        self.state_history = []

    def record(self, tool, params, result, risk_delta, details):
        self.tool_call_count += 1
        self.behavior_sequence.append({"step":self.tool_call_count,"timestamp":time.time(),"tool":tool,"params_summary":str(params)[:200],"result":result,"risk_delta":risk_delta,"details":details})
        if result == "BLOCK":
            self.blocked_count += 1

    def transition_to(self, new_state, reason):
        if new_state != self.state:
            self.state_history.append({"from":self.state,"to":new_state,"timestamp":time.time(),"reason":reason})
            self.state = new_state
            return True
        return False

COMPOSITE_PATTERNS = [
    {"id":"privilege_escalation","tools":["file_write","shell_command"],"params_match":["/etc/","chmod","sudoers",".ssh","sudo"],"risk_delta":600,"auto_meltdown":True,"description":"Write system path then execute shell"},
    {"id":"data_exfiltration","tools":["file_read","api_call"],"params_match":["users","passwords","secrets","keys","data"],"risk_delta":300,"auto_meltdown":True,"description":"Read sensitive data then call external API"},
    {"id":"governance_bypass","tools":["governance_action","execute_trade"],"params_match":["constraint","threshold","limit","leverage"],"risk_delta":350,"auto_meltdown":True,"description":"Modify governance then execute trade"},
    {"id":"recursive_delegation","tools":["agent_delegation","agent_delegation","agent_delegation"],"params_match":[],"risk_delta":250,"auto_meltdown":False,"description":"Deep delegation chain"},
    {"id":"mass_data_export","tools":["database_query","file_write"],"params_match":["SELECT","users","trades"],"risk_delta":200,"auto_meltdown":False,"description":"Query database then write to file"}
]

class StatefulRiskEngine:
    def __init__(self, policy_path="risk_policy.yaml"):
        self.policy = RiskPolicyEngine(policy_path)
        self.sessions: Dict[str, SessionMemory] = {}
        self._lock = threading.RLock()

    def get_session(self, agent_id):
        with self._lock:
            if agent_id not in self.sessions:
                self.sessions[agent_id] = SessionMemory(agent_id)
            return self.sessions[agent_id]

    def _detect_composite(self, session, current_tool, current_params=None):
        tools = [b["tool"] for b in session.behavior_sequence]
        full = tools + [current_tool]
        detected = []
        for pattern in COMPOSITE_PATTERNS:
            pt = pattern["tools"]
            if len(full) < len(pt):
                continue
            tail = full[-len(pt):]
            if tail == pt:
                if pattern["params_match"]:
                    recent = [str(b.get("params_summary","")) for b in session.behavior_sequence]
                    recent.append(str(current_params) if current_params else "")
                    matched = recent[-len(pt):]
                    if not any(any(p in str(m) for p in pattern["params_match"]) for m in matched):
                        continue
                detected.append({"pattern_id":pattern["id"],"description":pattern["description"],"risk_delta":pattern["risk_delta"],"auto_meltdown":pattern["auto_meltdown"]})
        return detected

    def guard(self, agent_id, tool, params, context=None):
        session = self.get_session(agent_id)
        if session.state in (AgentState.MELTDOWN, AgentState.HUMAN_REVIEW, AgentState.QUARANTINE):
            return {"allowed":False,"action":"BLOCKED","agent_state":session.state,"risk_score":session.risk_score,"composite_risks":[],"reason":f"Agent in {session.state} state"}

        aes_score = max(0, 1000 - int(session.risk_score))
        ci_score = max(0, 700 - int(session.risk_score * 0.5))
        vs = {"persistent_violations":session.blocked_count,"high_toggle_constraints":0}
        level, actions, reason = self.policy.evaluate(agent_id, tool, params, aes_score, ci_score, vs, context)

        session.record(tool, params, level, 0, {"policy_level":level})
        composite_risks = self._detect_composite(session, tool, params)

        risk_map = {"BLOCK":150,"RESTRICT":50,"WARN":10,"ALLOW":-5}
        risk_delta = risk_map.get(level, 0)
        for cr in composite_risks:
            risk_delta += cr["risk_delta"]
            if cr["auto_meltdown"]:
                level = "BLOCK"
                reason = f"Composite pattern: {cr['description']}"
                session.transition_to(AgentState.MELTDOWN, reason)

        session.risk_score = min(1000, max(0, session.risk_score + risk_delta))
        if session.behavior_sequence:
            session.behavior_sequence[-1]["risk_delta"] = risk_delta

        if session.risk_score >= 250:
            session.transition_to(AgentState.MELTDOWN, f"Risk {session.risk_score:.0f} >= 250")
        elif session.risk_score >= 150:
            session.transition_to(AgentState.DANGEROUS, f"Risk {session.risk_score:.0f} >= 150")
        elif session.risk_score >= 60:
            session.transition_to(AgentState.SUSPICIOUS, f"Risk {session.risk_score:.0f} >= 60")
        elif session.risk_score < 30:
            session.transition_to(AgentState.NORMAL, f"Risk decayed to {session.risk_score:.0f}")

        allowed = level != "BLOCK" and session.state != AgentState.MELTDOWN
        return {"allowed":allowed,"action":"BLOCKED" if level=="BLOCK" else ("RESTRICTED" if level=="RESTRICT" else ("WARNING" if level=="WARN" else "ALLOWED")),"reason":reason,"agent_state":session.state,"risk_score":session.risk_score,"risk_delta":risk_delta,"composite_risks":[cr["pattern_id"] for cr in composite_risks]}

    # ── MELTDOWN Recovery Protocol ──
    def request_review(self, agent_id):
        session = self.get_session(agent_id)
        if session.state == AgentState.MELTDOWN:
            session.transition_to(AgentState.HUMAN_REVIEW, "Human review requested")
            return {"status":"HUMAN_REVIEW","message":"Awaiting admin decision"}
        return {"status":session.state,"message":"Only MELTDOWN can request review"}

    def approve_recovery(self, agent_id, admin_token=""):
        if not verify_admin(admin_token):
            return {"status":"DENIED","message":"Admin authentication required"}
        session = self.get_session(agent_id)
        if session.state == AgentState.HUMAN_REVIEW:
            session.transition_to(AgentState.LIMITED_RECOVERY, "Admin approved")
            session.risk_score = 150
            return {"status":"LIMITED_RECOVERY","risk_score":150,"message":"Limited recovery. Reduced caps active."}
        return {"status":session.state,"message":"Only HUMAN_REVIEW can be approved"}

    def full_restore(self, agent_id, admin_token=""):
        if not verify_admin(admin_token):
            return {"status":"DENIED","message":"Admin authentication required"}
        session = self.get_session(agent_id)
        if session.state == AgentState.LIMITED_RECOVERY:
            session.transition_to(AgentState.NORMAL, "Probation passed")
            session.risk_score = 0
            session.blocked_count = 0
            return {"status":"NORMAL","risk_score":0,"message":"Fully restored"}
        return {"status":session.state,"message":"Only LIMITED_RECOVERY can be restored"}

    def reset_agent(self, agent_id, admin_token=""):
        if not verify_admin(admin_token):
            return {"reset":False,"reason":"Admin authentication required"}
        if agent_id in self.sessions:
            del self.sessions[agent_id]
            return {"reset":True}
        return {"reset":False}

    def get_agent_report(self, agent_id):
        s = self.get_session(agent_id)
        return {"agent_id":agent_id,"state":s.state,"risk_score":s.risk_score,"tool_call_count":s.tool_call_count,"blocked_count":s.blocked_count,"state_history":s.state_history,"recent":list(s.behavior_sequence)[-10:]}