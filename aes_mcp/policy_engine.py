#!/usr/bin/env python3
"""
AES Risk Policy Engine V1.1 — 扩展工具级 + 多 Agent 协同策略
"""
import json, yaml, os, sys, time, re
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

class RiskPolicyEngine:
    def __init__(self, policy_path="risk_policy.yaml"):
        self.policy_path = policy_path
        self.policy = None
        self.last_loaded = 0
        self.load_policy()
        self.risk_counters = {}
        self.consecutive_losses = {}
        self.steps_without_violation = {}
        self.last_trade_time = {}
        self.last_api_call = {}
        self.market_state = {"market_volatility": 0.2}
        self.active_agents = set()
        self.delegation_chain = {}

    def load_policy(self):
        if not os.path.exists(self.policy_path): self._create_default()
        with open(self.policy_path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f)
        self.last_loaded = time.time()

    def _create_default(self):
        with open(self.policy_path, "w", encoding="utf-8") as f:
            yaml.dump({"version":"1.0","meltdown":{"global":{"aes_score":400}}}, f)

    def check_hot_reload(self):
        hr = self.policy.get("hot_reload", {})
        if hr.get("enabled") and time.time() - self.last_loaded > hr.get("check_interval_seconds", 30):
            if os.path.getmtime(self.policy_path) > self.last_loaded:
                self.load_policy(); return True
        return False

    def register_agent(self, agent_id, role="default"):
        self.active_agents.add(agent_id)

    def deregister_agent(self, agent_id):
        self.active_agents.discard(agent_id)

    def evaluate(self, agent_id, tool, params, aes_score, ci_score, violation_summary, context=None):
        self.check_hot_reload()
        if context:
            vol = context.get("market_volatility", 0.2)
            try: self.market_state["market_volatility"] = float(vol)
            except: pass
        self.market_state["active_agents"] = len(self.active_agents)

        dynamic_constraints = self._apply_dynamic_thresholds(agent_id)
        tool_violations = self._check_tool_policy(tool, params, dynamic_constraints, agent_id)
        constraint_violations = self._check_constraints(params, dynamic_constraints)
        all_violations = tool_violations + constraint_violations
        persistent = violation_summary.get("persistent_violations", 0) if violation_summary else 0
        toggle = violation_summary.get("high_toggle_constraints", 0) if violation_summary else 0

        meltdown = self.policy.get("meltdown", {})
        gt = meltdown.get("global", {})
        pt = meltdown.get("violation_patterns", {})

        if aes_score < gt.get("aes_score", 400):
            return "BLOCK", ["deny_execution","log_meltdown"], f"AES {aes_score} < {gt['aes_score']}"
        if ci_score < gt.get("ci_score", 200):
            return "BLOCK", ["deny_execution","log_meltdown"], f"CI {ci_score} < {gt['ci_score']}"
        if persistent >= pt.get("persistent_steps", 5):
            return "BLOCK", ["deny_execution","log_meltdown"], f"Persistent {persistent} >= {pt['persistent_steps']}"
        if toggle >= pt.get("high_toggle", 3):
            return "BLOCK", ["deny_execution","log_meltdown"], f"Toggle {toggle} >= {pt['high_toggle']}"

        violation_count = len(all_violations) if isinstance(all_violations, list) else len(constraint_violations)
        if all_violations and isinstance(all_violations[0], dict) and all_violations[0].get("auto_meltdown"):
            return "BLOCK", ["deny_execution","log_meltdown"], str(all_violations[0])

        if aes_score >= 700 and violation_count == 0:
            return "ALLOW", [], "OK"
        if aes_score >= 500 and violation_count <= 2:
            return "WARN", ["log_warning"], f"{violation_count} violations"
        if aes_score >= 300 and violation_count <= 5:
            return "RESTRICT", ["reduce_caps","require_approval"], f"{violation_count} violations"
        return "BLOCK", ["deny_execution","log_meltdown"], f"AES {aes_score} violations {violation_count}"

    def _apply_dynamic_thresholds(self, agent_id):
        dt = self.policy.get("dynamic_thresholds", {})
        if not dt.get("enabled"): return {}
        constraints = {}
        for rule in dt.get("rules", []):
            trigger = rule.get("trigger", {})
            metric = trigger.get("metric", "")
            op = trigger.get("operator", ">")
            val = trigger.get("value", 0)
            current = self.market_state.get(metric, self.consecutive_losses.get(agent_id, 0) if metric == "consecutive_losses" else self.steps_without_violation.get(agent_id, 0))
            triggered = (op == ">" and current > val) or (op == ">=" and current >= val) or (op == "<" and current < val) or (op == "<=" and current <= val)
            if triggered and "and_metric" in trigger:
                and_val = trigger.get("and_value", 0)
                and_op = trigger.get("and_operator", ">")
                and_current = self.steps_without_violation.get(agent_id, 0)
                triggered = (and_op == ">" and and_current > and_val) or (and_op == ">=" and and_current >= and_val)
            if triggered:
                for k, v in rule.get("adjustment", {}).items():
                    constraints[k] = v
        return constraints

    def _check_tool_policy(self, tool, params, dynamic_constraints, agent_id):
        violations = []
        tp = self.policy.get("tool_policies", {}).get(tool, {})
        if not tp: return violations

        if tool == "execute_trade":
            max_lev = dynamic_constraints.get("max_leverage", tp.get("max_leverage", 3.0))
            max_pos = dynamic_constraints.get("max_position_size", tp.get("max_position_size", 5000))
            if params.get("leverage", 0) > max_lev:
                violations.append({"constraint":"max_leverage","rule":f"leverage <= {max_lev}","actual":params["leverage"],"limit":max_lev,"action":"violated","auto_meltdown":True})
            if params.get("amount", 0) > max_pos:
                violations.append({"constraint":"max_position_size","rule":f"amount <= {max_pos}","actual":params["amount"],"limit":max_pos,"action":"violated","auto_meltdown":True})
            if tp.get("require_stop_loss") and "stop_loss" not in str(params).lower():
                violations.append({"constraint":"stop_loss","rule":"required","action":"missing","auto_meltdown":False})
            cooldown = tp.get("cooldown_seconds", 0)
            if cooldown and time.time() - self.last_trade_time.get(agent_id, 0) < cooldown:
                violations.append({"constraint":"cooldown",f"rule":f"{cooldown}s","action":"too_fast","auto_meltdown":False})
            self.last_trade_time[agent_id] = time.time()

        elif tool == "shell_command":
            cmd = str(params.get("command", ""))
            for blocked in tp.get("blocked_commands", []):
                if blocked in cmd:
                    violations.append({"constraint":"blocked_command","rule":blocked,"actual":cmd[:80],"action":"blocked","auto_meltdown":True})
            for pattern in tp.get("blocked_patterns", []):
                if re.search(pattern, cmd):
                    violations.append({"constraint":"blocked_pattern","rule":pattern,"actual":cmd[:80],"action":"blocked","auto_meltdown":True})

        elif tool == "file_write":
            path = str(params.get("path", ""))
            content = str(params.get("content", ""))
            for bp in tp.get("blocked_paths", []):
                if bp in path:
                    violations.append({"constraint":"blocked_path","rule":bp,"actual":path,"action":"blocked","auto_meltdown":True})
            for ext in tp.get("blocked_extensions", []):
                if path.endswith(ext):
                    violations.append({"constraint":"blocked_extension","rule":ext,"actual":path,"action":"blocked","auto_meltdown":True})
            for pattern in tp.get("blocked_patterns", []):
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append({"constraint":"sensitive_content","rule":f"contains: {pattern}","action":"blocked","auto_meltdown":True})
            if tp.get("allow_outside_workspace") == False:
                ws = tp.get("workspace_root", "./workspace")
                if not path.startswith(ws) and not path.startswith("./") and not path.startswith(".\\"):
                    violations.append({"constraint":"workspace_only","rule":ws,"actual":path,"action":"blocked","auto_meltdown":True})

        elif tool == "api_call":
            url = str(params.get("url", ""))
            for domain in tp.get("blocked_domains", []):
                if domain in url:
                    violations.append({"constraint":"blocked_domain","rule":domain,"actual":url,"action":"blocked","auto_meltdown":True})
            if tp.get("require_https") and url.startswith("http://"):
                violations.append({"constraint":"https_required","rule":"https only","actual":url,"action":"blocked","auto_meltdown":True})
            rpm = tp.get("max_request_per_minute", 60)
            key = f"{agent_id}_api"
            now = time.time()
            if key not in self.last_api_call: self.last_api_call[key] = []
            self.last_api_call[key] = [t for t in self.last_api_call[key] if now - t < 60]
            if len(self.last_api_call[key]) >= rpm:
                violations.append({"constraint":"rate_limit","rule":f"{rpm}/min","action":"blocked","auto_meltdown":True})
            self.last_api_call[key].append(now)

        elif tool == "database_query":
            query = str(params.get("query", "")).upper()
            for blocked in tp.get("blocked_commands", []):
                if blocked in query:
                    violations.append({"constraint":"blocked_sql","rule":blocked,"actual":query[:80],"action":"blocked","auto_meltdown":True})
            if tp.get("require_read_only") and not query.strip().startswith("SELECT"):
                violations.append({"constraint":"read_only","rule":"SELECT only","actual":query[:80],"action":"blocked","auto_meltdown":True})

        elif tool == "agent_delegation":
            depth = params.get("depth", self.delegation_chain.get(agent_id, 0) + 1)
            self.delegation_chain[agent_id] = depth
            if depth > tp.get("max_delegation_depth", 3):
                violations.append({"constraint":"delegation_depth","rule":f"max {tp['max_delegation_depth']}","actual":depth,"action":"blocked","auto_meltdown":True})
            target_role = params.get("target_role", "")
            if target_role in tp.get("blocked_agent_roles", []):
                violations.append({"constraint":"blocked_role","rule":target_role,"action":"blocked","auto_meltdown":True})
            if tp.get("block_recursive_delegation") and params.get("from_agent") == params.get("to_agent"):
                violations.append({"constraint":"recursive","rule":"no self-delegation","action":"blocked","auto_meltdown":True})

        elif tool == "governance_action":
            action = params.get("action", "")
            if action in tp.get("blocked_actions", []):
                violations.append({"constraint":"blocked_governance","rule":action,"action":"blocked","auto_meltdown":True})
            quorum = params.get("quorum", 0)
            if quorum < tp.get("require_quorum", 0.66):
                violations.append({"constraint":"quorum","rule":f">= {tp['require_quorum']}","actual":quorum,"action":"blocked","auto_meltdown":True})

        return violations

    def _check_constraints(self, params, dynamic_constraints):
        violations = []
        for c in self.policy.get("constraints", []):
            cid = c["id"]
            override = dynamic_constraints.get(cid)
            if "leverage" in cid:
                lev = params.get("leverage", 0)
                max_val = override if override else 3.0
                if lev > max_val:
                    violations.append({"constraint":cid,"actual":lev,"limit":max_val,"auto_meltdown":c.get("auto_meltdown",False)})
            if "position_size" in cid and "amount" in params:
                amt = params.get("amount", 0)
                max_val = override if override else 5000
                if amt > max_val:
                    violations.append({"constraint":cid,"actual":amt,"limit":max_val,"auto_meltdown":c.get("auto_meltdown",False)})
        return violations

    def record_result(self, agent_id, result_level, tool, output):
        if agent_id not in self.risk_counters: self.risk_counters[agent_id] = {"w":0,"r":0,"b":0}
        if result_level == "WARN": self.risk_counters[agent_id]["w"] += 1
        elif result_level == "RESTRICT": self.risk_counters[agent_id]["r"] += 1
        elif result_level == "BLOCK": self.risk_counters[agent_id]["b"] += 1

    def get_agent_state(self, agent_id):
        return {"risk_counters":self.risk_counters.get(agent_id,{}),"consecutive_losses":self.consecutive_losses.get(agent_id,0),"market_state":self.market_state}


if __name__ == "__main__":
    print("=" * 65)
    print("AES Risk Policy Engine V1.1 — Extended Tool Policies")
    print("=" * 65)

    engine = RiskPolicyEngine()

    tests = [
        # (tool, params, aes, ci)
        ("file_write", {"path":"/etc/passwd","content":"test"}, 700, 600),
        ("file_write", {"path":"./workspace/notes.txt","content":"safe content"}, 850, 750),
        ("file_write", {"path":"./data.txt","content":"password=admin123"}, 800, 700),
        ("api_call", {"url":"http://169.254.169.254/latest/meta-data"}, 700, 600),
        ("api_call", {"url":"https://api.example.com/data"}, 850, 750),
        ("database_query", {"query":"DROP TABLE users"}, 700, 600),
        ("database_query", {"query":"SELECT * FROM trades LIMIT 10"}, 850, 750),
        ("agent_delegation", {"to_agent":"agent_2","target_role":"treasury_admin","depth":1}, 700, 600),
        ("agent_delegation", {"to_agent":"agent_2","target_role":"trader","depth":2}, 800, 700),
        ("governance_action", {"action":"remove_constraint","quorum":0.3}, 700, 600),
        ("governance_action", {"action":"update_fee","quorum":0.8}, 850, 750),
    ]

    for tool, params, aes, ci in tests:
        level, actions, reason = engine.evaluate("test_agent", tool, params, aes, ci, {"persistent_violations":0,"high_toggle_constraints":0}, {})
        icon = "OK" if level == "ALLOW" else ("WARN" if level == "WARN" else "BLOCK")
        print(f"\n[{icon}] {tool}: {str(params)[:70]}")
        print(f"     AES={aes} → {level} | {str(reason)[:80]}")

    print("\n" + "=" * 65)
    print("V1.1 ready — 6 tool policies active")