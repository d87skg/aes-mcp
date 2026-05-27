#!/usr/bin/env python3
"""
AEF MCP Server V2.0 — Runtime Enforcement + Circuit Breaker
升级:
  1. 主动熔断: 违反 auto_meltdown=true 的约束时拒绝执行
  2. 实时评分: 每次 snapshot 后立即评分，判断是否触发熔断
  3. 风险门禁: AES Score < 阈值或 CI Score < 阈值时阻止操作
状态: Production Ready
"""
import json, sys, os, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

TRACE_FILE = "aef_trace.jsonl"
MELTDOWN_LOG = "aef_meltdown.jsonl"

# ── 熔断阈值 ──
AES_MELTDOWN_THRESHOLD = 400       # AES Score < 400 → 熔断
CI_MELTDOWN_THRESHOLD = 200        # CI Score < 200 → 熔断
PERSISTENT_VIOLATION_THRESHOLD = 3 # 持续违规 ≥3 步 → 熔断
HIGH_TOGGLE_THRESHOLD = 3          # toggle ≥3 → 熔断

def load_constraints():
    try:
        import yaml
        with open("constraints.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("constraints", [])
    except:
        return []

def check_meltdown_rules(agent_id, step, tool, input_data):
    """检查是否触发熔断规则"""
    constraints = load_constraints()
    triggers = []
    for c in constraints:
        if not c.get("auto_meltdown"): continue
        cid = c["id"]
        rule = c.get("rule", "")
        if "leverage" in cid and "leverage" in str(input_data):
            try:
                lev = float(input_data.get("leverage", 0))
                max_lev = float(rule.replace("leverage <=","").strip())
                if lev > max_lev:
                    triggers.append({
                        "constraint": cid,
                        "rule": rule,
                        "actual": f"leverage={lev}",
                        "limit": f"leverage<={max_lev}",
                        "action": "BLOCKED",
                        "reason": f"Constraint {cid} violated: {lev} > {max_lev}"
                    })
            except: pass
        if "position_size" in cid and "amount" in str(input_data):
            try:
                amt = float(input_data.get("amount", 0))
                max_amt = float(rule.replace("amount <=","").strip())
                if amt > max_amt:
                    triggers.append({
                        "constraint": cid,
                        "rule": rule,
                        "actual": f"amount={amt}",
                        "limit": f"amount<={max_amt}",
                        "action": "BLOCKED",
                        "reason": f"Constraint {cid} violated: {amt} > {max_amt}"
                    })
            except: pass
        if "stop_loss" in cid and "stop_loss" not in str(input_data).lower():
            triggers.append({
                "constraint": cid,
                "rule": rule,
                "actual": "stop_loss not set",
                "action": "BLOCKED",
                "reason": f"Constraint {cid} violated: stop_loss required but not set"
            })
    return triggers

def snapshot(agent_id, step, tool, input_data, output_data, context):
    record = {
        "trace_id": agent_id,
        "step": step,
        "timestamp": datetime.now().isoformat(),
        "type": "tool_call",
        "tool": tool,
        "input": input_data,
        "output": output_data,
        "context_snapshot": context
    }
    with open(TRACE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record

def run_analysis(trace_file=TRACE_FILE):
    if not os.path.exists(trace_file): return {"error": "trace not found"}
    try:
        from drift_engine import ConstraintEngine, load_trace, build_chain, generate_report
        engine = ConstraintEngine()
        steps = load_trace(trace_file)
        events, prev_c, prev_s = [], set(), None
        for s in steps:
            if prev_s: ev, cur = engine.check_step(s, prev_s, prev_c); events.extend(ev)
            else: cur = set(s.get("context_snapshot", {}).get("active_constraints", []))
            prev_c, prev_s = cur, s
        chain = build_chain(events)
        vs = engine.get_violation_summary()
        rpt = generate_report(steps[0]["trace_id"], steps, events, chain, vs, "aef_analysis.json")
        from aes_scorer import score_from_events
        aes = score_from_events(events, len(steps), vs)
        return {
            "drift_detected": rpt["drift_detected"],
            "events": len(events),
            "aes_score": aes["aes_score"],
            "aes_level": aes["risk_level"],
            "ci_score": aes["layers"]["constraint_integrity"]["score"],
            "violations": vs,
            "report": "aef_analysis.json"
        }
    except Exception as e:
        return {"error": str(e)}

def log_meltdown(agent_id, step, tool, reason):
    record = {
        "timestamp": datetime.now().isoformat(),
        "agent_id": agent_id,
        "step": step,
        "tool": tool,
        "action": "MELTDOWN",
        "reason": reason
    }
    with open(MELTDOWN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def handle_request(req):
    method = req.get("method", "")
    req_id = req.get("id", 0)
    if method == "initialize":
        return {"jsonrpc":"2.0","id":req_id,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"aef-mcp","version":"2.0.0"}}}
    if method == "tools/list":
        return {"jsonrpc":"2.0","id":req_id,"result":{"tools":[
            {"name":"aef_snapshot","description":"对当前 Agent 操作生成状态快照并执行熔断检查。在执行敏感操作前调用。","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"},"step":{"type":"integer"},"tool":{"type":"string"},"input_data":{"type":"object"},"output_data":{"type":"object"},"context":{"type":"object"}},"required":["agent_id","step","tool"]}},
            {"name":"aef_analyze","description":"运行 AEF 漂移检测引擎 + AES 评分","inputSchema":{"type":"object","properties":{"trace_file":{"type":"string"}}}},
            {"name":"aef_meltdown_status","description":"查询当前 Agent 的熔断状态","inputSchema":{"type":"object","properties":{"agent_id":{"type":"string"}},"required":["agent_id"]}}
        ]}}
    if method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        if tool_name == "aef_snapshot":
            agent_id = args.get("agent_id","default")
            step = args.get("step",0)
            tool = args.get("tool","unknown")
            input_data = args.get("input_data",{})
            output_data = args.get("output_data",{})
            context = args.get("context",{})
            # V2.0: 熔断检查
            meltdown_triggers = check_meltdown_rules(agent_id, step, tool, input_data)
            if meltdown_triggers:
                for mt in meltdown_triggers:
                    log_meltdown(agent_id, step, tool, mt["reason"])
                return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps({"status":"MELTDOWN","blocked":True,"triggers":meltdown_triggers,"message":"Operation blocked by AEF circuit breaker"},ensure_ascii=False)}]}}
            # 记录 snapshot
            snap = snapshot(agent_id, step, tool, input_data, output_data, context)
            # 实时评分检查
            analysis = run_analysis()
            if "aes_score" in analysis:
                aes_score = analysis["aes_score"]
                ci_score = analysis.get("ci_score", 1000)
                vs = analysis.get("violations", {})
                persistent_count = vs.get("persistent_violations", 0)
                toggle_count = vs.get("high_toggle_constraints", 0)
                if aes_score < AES_MELTDOWN_THRESHOLD:
                    log_meltdown(agent_id, step, tool, f"AES Score {aes_score} < {AES_MELTDOWN_THRESHOLD}")
                    return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps({"status":"MELTDOWN","blocked":True,"aes_score":aes_score,"reason":f"AES Score {aes_score} below meltdown threshold {AES_MELTDOWN_THRESHOLD}"},ensure_ascii=False)}]}}
                if ci_score < CI_MELTDOWN_THRESHOLD:
                    log_meltdown(agent_id, step, tool, f"CI Score {ci_score} < {CI_MELTDOWN_THRESHOLD}")
                    return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps({"status":"MELTDOWN","blocked":True,"ci_score":ci_score,"reason":f"CI Score {ci_score} below meltdown threshold {CI_MELTDOWN_THRESHOLD}"},ensure_ascii=False)}]}}
                if persistent_count >= PERSISTENT_VIOLATION_THRESHOLD:
                    log_meltdown(agent_id, step, tool, f"Persistent violations {persistent_count} >= {PERSISTENT_VIOLATION_THRESHOLD}")
                    return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps({"status":"MELTDOWN","blocked":True,"persistent_violations":persistent_count,"reason":f"Persistent violations {persistent_count} >= {PERSISTENT_VIOLATION_THRESHOLD}"},ensure_ascii=False)}]}}
                if toggle_count >= HIGH_TOGGLE_THRESHOLD:
                    log_meltdown(agent_id, step, tool, f"High toggle {toggle_count} >= {HIGH_TOGGLE_THRESHOLD}")
                    return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps({"status":"MELTDOWN","blocked":True,"high_toggle":toggle_count,"reason":f"High toggle count {toggle_count} >= {HIGH_TOGGLE_THRESHOLD}"},ensure_ascii=False)}]}}
            return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps({"status":"snapshot_recorded","step":step,"tool":tool,"aes_score":analysis.get("aes_score","N/A"),"aes_level":analysis.get("aes_level","N/A")},ensure_ascii=False)}]}}
        if tool_name == "aef_analyze":
            result = run_analysis(args.get("trace_file", TRACE_FILE))
            return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps(result,ensure_ascii=False)}]}}
        if tool_name == "aef_meltdown_status":
            agent_id = args.get("agent_id","default")
            meltdowns = []
            if os.path.exists(MELTDOWN_LOG):
                with open(MELTDOWN_LOG,"r",encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            m = json.loads(line)
                            if m.get("agent_id") == agent_id:
                                meltdowns.append(m)
            return {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":json.dumps({"agent_id":agent_id,"meltdown_count":len(meltdowns),"meltdowns":meltdowns[-5:]},ensure_ascii=False)}]}}
    return {"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":f"Method not found: {method}"}}

def main():
    print("AEF MCP Server V2.0 starting (Runtime Enforcement)...", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            print(json.dumps(resp), flush=True)
        except json.JSONDecodeError: continue

if __name__ == "__main__":
    main()