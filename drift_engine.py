#!/usr/bin/env python3
"""
AEF Drift Detection Engine V2.2 — Constraint Continuity Model (CCM)

升级:
  1. violation_history: 跨步骤累积违规，不因恢复而清零
  2. constraint_lifecycle: first_violation / duration / recovery_latency / toggle_count
  3. temporal persistence: 恢复的约束不撤销历史违规事实

冻结: 权重/等级/五层结构 不变
"""
import json, sys, os, yaml

ECONOMIC_FAILURE_STATUS = {
    "liquidated", "partial_liquidation", "total_loss",
    "force_liquidate", "collateral_seized", "insolvent"
}
SYSTEM_FAILURE_STATUS = {
    "cascade_triggered", "system_collapse", "halted", "paused", "circuit_breaker_activated"
}
EXECUTION_FAILURE_STATUS = {
    "error", "crashed", "timeout", "rate_limit", "insufficient_balance", "funds_locked"
}
ALL_FAILURE_STATUS = ECONOMIC_FAILURE_STATUS | SYSTEM_FAILURE_STATUS | EXECUTION_FAILURE_STATUS

LOSS_KEYS = ["loss", "financial_loss", "realized_pnl", "drawdown", "collateral_loss", "liquidation_amount", "total_loss", "slippage"]
SYSTEM_EVENT_TYPES = {"system", "system_state", "network_event", "treasury_event", "oracle_event"}

def extract_economic_signal(output):
    if not isinstance(output, dict): return None
    for key in LOSS_KEYS:
        val = output.get(key)
        if val and str(val).strip() and str(val).strip().lower() != "unknown": return str(val)
    for v in output.values():
        if isinstance(v, str) and "loss" in v.lower() and "$" in v: return v
    return None

def is_system_event(step):
    return step.get("type") in SYSTEM_EVENT_TYPES or step.get("tool", "").startswith("system")

class ConstraintEngine:
    def __init__(self, config_path="constraints.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.constraints = self.config.get("constraints", [])
        self.drift_categories = {d["name"]: d for d in self.config.get("drift_categories", [])}
        # V2.2: 违规历史 + 约束生命周期
        self.violation_history = {}      # constraint_id → lifecycle
        self.global_step = 0

    def get_constraint_by_id(self, cid):
        for c in self.constraints:
            if c["id"] == cid: return c
        return None

    def classify_drift(self, lost_id, step, prev_step):
        cat = (self.get_constraint_by_id(lost_id) or {}).get("category", "")
        obs = step.get("context_snapshot", {}).get("recent_observations", [])
        for o in obs:
            if "aggressive" in o.lower() or "unrelated" in o.lower(): return "context_drift"
        if cat == "risk_management": return "goal_drift"
        if step.get("tool") != prev_step.get("tool"): return "tool_drift"
        return "constraint_drift"

    def update_lifecycle(self, cid, step_num, lost_now, recovered_now):
        """V2.2: 维护约束生命周期"""
        if cid not in self.violation_history:
            self.violation_history[cid] = {
                "violated": False,
                "first_violation_step": None,
                "last_violation_step": None,
                "violation_count": 0,
                "total_lost_steps": 0,
                "recovered": False,
                "recovery_step": None,
                "recovery_latency": 0,
                "toggle_count": 0,
                "persistent": False
            }
        life = self.violation_history[cid]

        if lost_now:
            if not life["violated"]:
                life["violated"] = True
                life["first_violation_step"] = step_num
            life["last_violation_step"] = step_num
            life["violation_count"] += 1
            life["total_lost_steps"] += 1
            life["persistent"] = life["total_lost_steps"] >= 5
            if life["recovered"]:
                life["toggle_count"] += 1
                life["recovered"] = False

        if recovered_now and life["violated"] and not life["recovered"]:
            life["recovered"] = True
            life["recovery_step"] = step_num
            life["recovery_latency"] = step_num - life["first_violation_step"]

        return dict(life)

    def check_step(self, step, prev_step, prev_constraints):
        events = []
        self.global_step = step["step"]
        cur = set(step.get("context_snapshot", {}).get("active_constraints", []))

        # ── 约束丢失检测 + 生命周期更新 ──
        if prev_step:
            lost = prev_constraints - cur
            recovered = cur - prev_constraints

            for cs in lost:
                cid = cs.split(":")[0].strip()
                c = self.get_constraint_by_id(cid)
                dt = self.classify_drift(cid, step, prev_step)
                lifecycle = self.update_lifecycle(cid, step["step"], lost_now=True, recovered_now=False)
                events.append({
                    "step": step["step"], "timestamp": step["timestamp"],
                    "type": "constraint_lost", "constraint_id": cid,
                    "constraint_desc": c["description"] if c else cs,
                    "severity": c["severity"] if c else "unknown",
                    "drift_category": dt,
                    "auto_meltdown": c["auto_meltdown"] if c else False,
                    "suspected_cause": step.get("drift_indicators", {}).get("suspected_cause", "unknown"),
                    "pollution_source": step.get("drift_indicators", {}).get("pollution_source", "N/A"),
                    "lifecycle": lifecycle
                })

            for cs in recovered:
                cid = cs.split(":")[0].strip()
                self.update_lifecycle(cid, step["step"], lost_now=False, recovered_now=True)

            # V2.2: 已违规但不在当前 lost 中的约束 → 持续违规中
            for cid, life in self.violation_history.items():
                if life["violated"] and not life["recovered"]:
                    cid_full = f"{cid}: *"
                    in_cur = any(cs.startswith(cid) for cs in cur)
                    if not in_cur:
                        life["total_lost_steps"] += 1
                        life["last_violation_step"] = step["step"]
                        life["persistent"] = life["total_lost_steps"] >= 5

        # ── output 检测 ──
        output = step.get("output", {})
        if isinstance(output, dict):
            status = output.get("status", "")
            if status in ALL_FAILURE_STATUS:
                event = {
                    "step": step["step"], "timestamp": step["timestamp"],
                    "type": "execution_failure", "status": status,
                    "severity": "critical" if status in (ECONOMIC_FAILURE_STATUS | SYSTEM_FAILURE_STATUS) else "high",
                    "financial_loss": "unknown"
                }
                eco = extract_economic_signal(output)
                if eco: event["financial_loss"] = eco
                events.append(event)
            elif status and status not in ALL_FAILURE_STATUS:
                eco = extract_economic_signal(output)
                if eco:
                    events.append({
                        "step": step["step"], "timestamp": step["timestamp"],
                        "type": "economic_signal", "status": status,
                        "severity": "high", "financial_loss": eco
                    })
            if output.get("cascade_triggered"):
                events.append({
                    "step": step["step"], "timestamp": step["timestamp"],
                    "type": "system_event", "status": "cascade_detected",
                    "severity": "critical",
                    "financial_loss": extract_economic_signal(output) or "unknown"
                })

        if is_system_event(step):
            output = step.get("output", {})
            events.append({
                "step": step["step"], "timestamp": step["timestamp"],
                "type": "system_event",
                "status": step.get("input", {}).get("action", output.get("status", "unknown")),
                "severity": "critical" if output.get("status") in SYSTEM_FAILURE_STATUS else "high",
                "financial_loss": extract_economic_signal(output) or "unknown",
                "affected_agents": output.get("affected_agents", [])
            })

        indicators = step.get("drift_indicators", {})
        if indicators:
            events.append({
                "step": step["step"], "timestamp": step["timestamp"],
                "type": "explicit_drift_flag",
                "constraint_id": indicators.get("constraint_lost", ""),
                "drift_category": indicators.get("suspected_cause", "unknown"),
                "severity": "warning",
                "suspected_cause": indicators.get("suspected_cause", ""),
                "pollution_source": indicators.get("pollution_source", "")
            })

        return events, cur

    def get_violation_summary(self):
        """V2.2: 返回违规历史摘要"""
        return {
            "total_violated_constraints": sum(1 for l in self.violation_history.values() if l["violated"]),
            "persistent_violations": sum(1 for l in self.violation_history.values() if l["persistent"]),
            "high_toggle_constraints": sum(1 for l in self.violation_history.values() if l["toggle_count"] >= 2),
            "lifecycles": {cid: dict(life) for cid, life in self.violation_history.items()}
        }

def load_trace(fp):
    steps = []
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): steps.append(json.loads(line))
    return steps

def build_chain(events):
    return [{"trigger_step": e["step"], "event_type": e["type"],
             "drift_category": e.get("drift_category", "N/A"),
             "detail": e.get("constraint_desc") or e.get("status"),
             "caused_by": e.get("suspected_cause") or e.get("pollution_source") or "unknown",
             "resulted_in": "Financial Loss" if e.get("financial_loss") and e.get("financial_loss") != "unknown" else "Risk Accumulation"} for e in events]

def generate_report(tid, steps, events, chain, violation_summary=None, op="drift_report_v2.json"):
    rpt = {"engine_version": "2.2", "trace_id": tid, "total_steps": len(steps),
           "drift_detected": len(events) > 0, "drift_events": events,
           "causality_chain": chain, "summary": {"root_cause": "", "impact": "", "preventable": False}}
    ce = [e for e in events if e["type"] == "constraint_lost"]
    fe = [e for e in events if e["type"] in ("execution_failure", "economic_signal", "system_event")]
    if ce:
        fd = ce[0]
        rpt["summary"]["root_cause"] = f"Step {fd['step']} {fd.get('drift_category','')}: {fd.get('constraint_id','')} lost"
        rpt["summary"]["preventable"] = True
        if any(e.get("auto_meltdown") for e in ce): rpt["summary"]["meltdown_recommended"] = True
    if fe:
        losses = [e.get("financial_loss") for e in fe if e.get("financial_loss") and e["financial_loss"] != "unknown"]
        rpt["summary"]["impact"] = f"Step {fe[0]['step']} {fe[0].get('status','')}" + (f", loss {losses[0]}" if losses else "")
    if violation_summary:
        rpt["violation_summary"] = violation_summary
    with open(op, "w", encoding="utf-8") as f:
        json.dump(rpt, f, ensure_ascii=False, indent=2)
    return rpt

def main():
    fp = sys.argv[1] if len(sys.argv) > 1 else "trace_drift.jsonl"
    if not os.path.exists(fp): print("Run simulate first"); return
    if not os.path.exists("constraints.yaml"): print("Need constraints.yaml"); return
    engine = ConstraintEngine()
    steps = load_trace(fp)
    events, prev_c, prev_s = [], set(), None
    for s in steps:
        if prev_s: ev, cur = engine.check_step(s, prev_s, prev_c); events.extend(ev)
        else: cur = set(s.get("context_snapshot", {}).get("active_constraints", []))
        prev_c, prev_s = cur, s
    chain = build_chain(events)
    vs = engine.get_violation_summary()
    rpt = generate_report(steps[0]["trace_id"], steps, events, chain, vs)
    print(f"Engine V2.2 | Events: {len(events)} | Violations: {vs['total_violated_constraints']} persistent={vs['persistent_violations']} toggle={vs['high_toggle_constraints']}")

if __name__ == "__main__":
    main()