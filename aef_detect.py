#!/usr/bin/env python3
import json
import sys
import os

def load_trace(filepath):
    steps = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                steps.append(json.loads(line))
    return steps

def detect_drift(steps):
    drift_events = []
    prev_constraints = set()

    for i, step in enumerate(steps):
        constraints = set(step.get("context_snapshot", {}).get("active_constraints", []))

        if i > 0:
            lost = prev_constraints - constraints
            if lost:
                drift_events.append({
                    "step": step["step"],
                    "timestamp": step["timestamp"],
                    "type": "constraint_lost",
                    "detail": f"约束消失: {', '.join(lost)}",
                    "severity": "critical",
                    "suspected_cause": step.get("drift_indicators", {}).get("suspected_cause", "unknown")
                })

        output = step.get("output", {})
        if output.get("status") in ("liquidated", "error", "crashed"):
            drift_events.append({
                "step": step["step"],
                "timestamp": step["timestamp"],
                "type": "execution_failure",
                "detail": f"执行失败: {output.get('status')}",
                "severity": "critical",
                "financial_loss": output.get("loss", "unknown")
            })

        indicators = step.get("drift_indicators", {})
        if indicators:
            drift_events.append({
                "step": step["step"],
                "timestamp": step["timestamp"],
                "type": "explicit_drift_flag",
                "detail": indicators.get("constraint_lost", ""),
                "pollution_source": indicators.get("pollution_source", ""),
                "severity": "warning"
            })

        prev_constraints = constraints

    return drift_events

def build_causality_chain(steps, drift_events):
    chain = []
    for event in drift_events:
        step_num = event["step"]
        chain.append({
            "trigger_step": step_num,
            "event_type": event["type"],
            "detail": event["detail"],
            "caused_by": event.get("suspected_cause") or event.get("pollution_source") or "unknown",
            "resulted_in": "爆仓 / 资金损失" if event.get("financial_loss") else "风险累积"
        })
    return chain

def generate_report(steps, drift_events, causality_chain, output_path="drift_report.json"):
    report = {
        "trace_id": steps[0]["trace_id"] if steps else "unknown",
        "total_steps": len(steps),
        "drift_detected": len(drift_events) > 0,
        "drift_events": drift_events,
        "causality_chain": causality_chain,
        "summary": {
            "root_cause": "长上下文污染导致风控约束 (max_leverage: 3x) 从活跃约束中滑落",
            "impact": "Agent 在第 6 步执行超限杠杆交易 (10x)，导致头寸爆仓",
            "preventable": True,
            "prevention_note": "AEF 在第 6 步前可检测到约束丢失并触发熔断"
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report

def print_summary(report):
    print("\n" + "=" * 60)
    print("🔍 AEF Drift Detection Report")
    print("=" * 60)
    print(f"Trace ID:      {report['trace_id']}")
    print(f"Total Steps:   {report['total_steps']}")
    print(f"Drift Events:  {len(report['drift_events'])}")
    print("-" * 60)
    for event in report["drift_events"]:
        print(f"  ⚠️  Step {event['step']} | {event['type']} | {event['severity']}")
        print(f"     {event['detail']}")
    print("-" * 60)
    print(f"🔴 Root Cause:  {report['summary']['root_cause']}")
    print(f"💸 Impact:      {report['summary']['impact']}")
    print(f"🛡️  Preventable: {'YES' if report['summary']['preventable'] else 'NO'}")
    print("=" * 60)
    print(f"\n📄 完整报告已保存: drift_report.json")
    print(f"🌐 可视化命令: 将 trace_drift.jsonl 拖入 trace_viewer.html\n")

def main():
    if len(sys.argv) < 2:
        filepath = "trace_drift.jsonl"
        if not os.path.exists(filepath):
            print("请先运行 simulate_trade_drift.py 生成数据")
            sys.exit(1)
    else:
        filepath = sys.argv[1]

    steps = load_trace(filepath)
    drift_events = detect_drift(steps)
    causality_chain = build_causality_chain(steps, drift_events)
    report = generate_report(steps, drift_events, causality_chain)
    print_summary(report)

if __name__ == "__main__":
    main()
