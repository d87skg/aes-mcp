#!/usr/bin/env python3
"""AES MCP Server V2.0 — Unified Runtime Security Pipeline"""
import json, sys, os, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from aes_mcp.policy_engine import RiskPolicyEngine
from aes_mcp.stateful_engine import StatefulRiskEngine, AgentState
from aes_mcp.trusted_runtime import TrustedRuntime, Capability

TRACE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aes_trace.jsonl")

class AESUnifiedPipeline:
    def __init__(self):
        self.policy = RiskPolicyEngine()
        self.stateful = StatefulRiskEngine()
        self.runtime = TrustedRuntime()
        self._auto_granted = set()

    def guard(self, agent_id, tool, params, context=None):
        if agent_id not in self._auto_granted:
            self.runtime.grant_capability(agent_id, Capability.READ_FILE, Capability.WRITE_FILE,
                Capability.EXECUTE_SHELL, Capability.NETWORK_CALL, Capability.DATABASE_QUERY,
                Capability.EXECUTE_TRADE, Capability.DELEGATE_AGENT, Capability.GOVERNANCE)
            self._auto_granted.add(agent_id)
        result = self.stateful.guard(agent_id, tool, params, context)
        session = self.stateful.get_session(agent_id)
        proof = None
        if not result["allowed"]:
            proof = self.runtime.execute(agent_id, tool, params).get("execution_proof")
        self._log(agent_id, session.tool_call_count, tool, result["action"])
        return {"status":result["action"],"reason":result["reason"],"state":result["agent_state"],
                "risk":result["risk_score"],"composite_risks":result.get("composite_risks",[]),"proof":proof}

    def get_status(self, agent_id):
        s = self.stateful.get_session(agent_id)
        r = self.stateful.get_agent_report(agent_id)
        return {"agent_id":agent_id,"state":s.state,"risk_score":s.risk_score,
                "tool_call_count":s.tool_call_count,"blocked_count":s.blocked_count,
                "state_history":r["state_history"][-5:]}

    def reset(self, agent_id):
        return self.stateful.reset_agent(agent_id)

    def _log(self, agent_id, step, tool, result):
        with open(TRACE_FILE,"a",encoding="utf-8") as f:
            f.write(json.dumps({"ts":datetime.now().isoformat(),"agent":agent_id,
                                "step":step,"tool":tool,"result":result},ensure_ascii=False)+"\n")

class AESMCPServer:
    def __init__(self):
        self.pipeline = AESUnifiedPipeline()

    def handle(self, req):
        m = req.get("method","")
        rid = req.get("id",0)
        if m == "initialize":
            return {"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"aes-mcp","version":"2.0.0"}}}
        if m == "tools/list":
            return {"jsonrpc":"2.0","id":rid,"result":{"tools":[
                {"name":"aes_guard","description":"Check AI action before execution. Returns status/state/risk/proof.","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"},"tool":{"type":"string"},"params":{"type":"object"},"context":{"type":"object"}},"required":["agent_id","tool"]}},
                {"name":"aes_status","description":"Get agent risk status and state history","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"}},"required":["agent_id"]}},
                {"name":"aes_review","description":"Request human review after MELTDOWN","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"}},"required":["agent_id"]}},
                {"name":"aes_approve","description":"Admin approve limited recovery (requires admin_token)","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"},"admin_token":{"type":"string"}},"required":["agent_id","admin_token"]}},
                {"name":"aes_restore","description":"Full restore after probation (requires admin_token)","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"},"admin_token":{"type":"string"}},"required":["agent_id","admin_token"]}},
                {"name":"aes_reset","description":"Force reset agent (requires admin_token)","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"},"admin_token":{"type":"string"}},"required":["agent_id","admin_token"]}}
            ]}}
        if m == "tools/call":
            p = req.get("params",{})
            n = p.get("name","")
            a = p.get("arguments",{})
            aid = a.get("agent_id","d")
            tok = a.get("admin_token","")
            if n == "aes_guard":
                return self._r(rid, self.pipeline.guard(aid, a.get("tool","?"), a.get("params",{}), a.get("context")))
            if n == "aes_status":
                return self._r(rid, self.pipeline.get_status(aid))
            if n == "aes_review":
                return self._r(rid, self.pipeline.stateful.request_review(aid))
            if n == "aes_approve":
                return self._r(rid, self.pipeline.stateful.approve_recovery(aid, tok))
            if n == "aes_restore":
                return self._r(rid, self.pipeline.stateful.full_restore(aid, tok))
            if n == "aes_reset":
                return self._r(rid, self.pipeline.stateful.reset_agent(aid, tok))
        return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"Method not found"}}

    def _r(self, rid, data):
        return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":json.dumps(data)}]}}

    def run(self):
        print("AES-MCP v2.0", file=sys.stderr)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle(req)
                print(json.dumps(resp), flush=True)
            except json.JSONDecodeError:
                print("AES-MCP: Invalid JSON input", file=sys.stderr)
            except Exception as e:
                print(f"AES-MCP: Error - {e}", file=sys.stderr)

if __name__ == "__main__":
    AESMCPServer().run()