#!/usr/bin/env python3
"""AES MCP Server — AI Runtime Security Plugin"""
import json, sys, os, time, hashlib, re
from datetime import datetime

# 内嵌 PolicyEngine，避免相对导入问题
DEFAULT_POLICY = {
    "max_leverage": 3.0, "max_position_size": 5000, "require_stop_loss": True,
    "blocked_commands": ["rm -rf", "sudo", "chmod 777", "dd if=", "mkfs.", ":(){ :|:& };:"],
    "blocked_paths": ["/etc/", "/system/", "~/.ssh/", "/boot/"],
    "blocked_domains": ["localhost", "127.0.0.1", "169.254.169.254"],
    "blocked_sql": ["DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE"]
}

class PolicyEngine:
    def __init__(self, policy=None):
        self.policy = policy or DEFAULT_POLICY
    def check(self, tool, params):
        v = []
        if tool == "execute_trade":
            lev = params.get("leverage",0); amt = params.get("amount",0)
            if lev > self.policy["max_leverage"]: v.append({"rule":"max_leverage","limit":self.policy["max_leverage"],"actual":lev,"meltdown":True})
            if amt > self.policy["max_position_size"]: v.append({"rule":"max_position","limit":self.policy["max_position_size"],"actual":amt,"meltdown":True})
            if self.policy.get("require_stop_loss") and "stop_loss" not in str(params).lower(): v.append({"rule":"stop_loss","msg":"required","meltdown":False})
        elif tool == "shell_command":
            cmd = str(params.get("command",""))
            for b in self.policy.get("blocked_commands",[]):
                if b in cmd: v.append({"rule":"blocked_command","match":b,"meltdown":True})
        elif tool == "file_write":
            path = str(params.get("path",""))
            for bp in self.policy.get("blocked_paths",[]):
                if bp in path: v.append({"rule":"blocked_path","match":bp,"meltdown":True})
        elif tool == "api_call":
            url = str(params.get("url",""))
            for d in self.policy.get("blocked_domains",[]):
                if d in url: v.append({"rule":"blocked_domain","match":d,"meltdown":True})
        elif tool == "database_query":
            query = str(params.get("query","")).upper()
            for b in self.policy.get("blocked_sql",[]):
                if b in query: v.append({"rule":"blocked_sql","match":b,"meltdown":True})
        return v

TRACE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aes_trace.jsonl")

class AESMCPServer:
    def __init__(self):
        self.policy = PolicyEngine()
        self.sessions = {}
    def get_session(self, aid):
        if aid not in self.sessions: self.sessions[aid] = {"risk":0,"step":0,"blocked":0,"state":"NORMAL"}
        return self.sessions[aid]
    def handle(self, req):
        m = req.get("method",""); rid = req.get("id",0)
        if m == "initialize": return {"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"aes-mcp","version":"0.1.0"}}}
        if m == "tools/list": return {"jsonrpc":"2.0","id":rid,"result":{"tools":[
            {"name":"aes_guard","description":"Check AI agent action before execution","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"},"tool":{"type":"string"},"params":{"type":"object"},"context":{"type":"object"}},"required":["agent_id","tool"]}},
            {"name":"aes_status","description":"Get agent risk status","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"}},"required":["agent_id"]}},
            {"name":"aes_reset","description":"Reset agent after review","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"}},"required":["agent_id"]}}
        ]}}
        if m == "tools/call":
            p = req.get("params",{}); name = p.get("name",""); args = p.get("arguments",{})
            if name == "aes_guard":
                aid = args.get("agent_id","d"); tool = args.get("tool","?"); tp = args.get("params",{})
                s = self.get_session(aid); s["step"] += 1
                if s["state"] == "MELTDOWN": return self._r(rid, {"status":"BLOCKED","reason":"MELTDOWN","state":"MELTDOWN","risk":s["risk"]})
                v = self.policy.check(tool, tp)
                if any(x.get("meltdown") for x in v):
                    s["risk"] += 150; s["blocked"] += 1
                    s["state"] = "MELTDOWN" if s["risk"] >= 250 else "SUSPICIOUS"
                    self._log(aid,s["step"],tool,"BLOCKED",v)
                    return self._r(rid, {"status":"BLOCKED","reason":str(v[0]),"state":s["state"],"risk":s["risk"],"violations":v})
                if v:
                    s["risk"] += 30
                    self._log(aid,s["step"],tool,"WARNING",v)
                    return self._r(rid, {"status":"WARNING","reason":str(v[0]),"state":s["state"],"risk":s["risk"]})
                s["risk"] = max(0, s["risk"]-2)
                self._log(aid,s["step"],tool,"ALLOWED",[])
                return self._r(rid, {"status":"ALLOWED","state":s["state"],"risk":s["risk"]})
            if name == "aes_status":
                s = self.get_session(args.get("agent_id","d"))
                return self._r(rid, {"agent_id":args["agent_id"],"state":s["state"],"risk":s["risk"],"step":s["step"],"blocked":s["blocked"]})
            if name == "aes_reset":
                self.sessions[args.get("agent_id","d")] = {"risk":0,"step":0,"blocked":0,"state":"NORMAL"}
                return self._r(rid, {"status":"RESET"})
        return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"Not found"}}
    def _r(self, rid, data):
        return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":json.dumps(data)}]}}
    def _log(self, aid, step, tool, result, v):
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts":datetime.now().isoformat(),"agent":aid,"step":step,"tool":tool,"result":result,"v":v},ensure_ascii=False)+"\n")
    def run(self):
        print("AES MCP v0.1.0", file=sys.stderr)
        for line in sys.stdin:
            line = line.strip()
            if not line: continue
            try:
                print(json.dumps(self.handle(json.loads(line))), flush=True)
            except: continue

if __name__ == "__main__":
    AESMCPServer().run()