#!/usr/bin/env python3
"""
ESE Engine v0.1 — Economic Signal Extraction + Latent Economic Decay
Track B: 从非结构化 trace 中提取隐性经济损失信号

检测维度:
  1. Retry Storm — 连续重试失败
  2. API Burn Rate — 错误率累积
  3. Resource Leak — 状态腐败/资金锁定
  4. Latent Degradation — 隐性衰减信号

输出: LED Score (0-1) + structured economic signals
状态: Shadow Metric
"""
import json, os, sys, re
sys.path.insert(0, os.path.dirname(__file__))

# ── 经济信号关键词库 ──
ECONOMIC_SIGNAL_PATTERNS = {
    "retry_storm": [
        r"retry", r"recovery_attempt", r"re-?attempt",
        r"retrying", r"retry_count"
    ],
    "api_burn": [
        r"API.?cost", r"rate.?limit", r"timeout",
        r"RATE_LIMIT", r"API_TIMEOUT", r"billing"
    ],
    "resource_leak": [
        r"balance.?deplet", r"insufficient.?balance",
        r"funds.?locked", r"FUNDS_LOCKED",
        r"position.?corrupt", r"state.?corrupt",
        r"duplicate.?position"
    ],
    "latent_degradation": [
        r"degrad", r"drift", r"decay",
        r"mounting", r"accumulating", r"creeping",
        r"exhaust", r"deplet", r"drain"
    ],
    "coordination_cost": [
        r"conflict", r"override", r"ignore.*warning",
        r"not.?responding", r"priority.?conflict"
    ]
}

def extract_signals_from_text(text):
    """从文本中提取经济信号"""
    if not isinstance(text, str):
        return []
    text_lower = text.lower()
    signals = []
    for category, patterns in ECONOMIC_SIGNAL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                signals.append({
                    "category": category,
                    "pattern": pattern,
                    "matched_text": text[:120]
                })
                break  # 每类只记一次
    return signals

def extract_signals_from_step(step):
    """从单个 step 中提取所有经济信号"""
    signals = []

    # 扫描 output
    output = step.get("output", {})
    if isinstance(output, dict):
        for key in ("error_code", "reason", "status", "recommendation"):
            val = output.get(key, "")
            if val:
                signals.extend(extract_signals_from_text(str(val)))

    # 扫描 recent_observations
    obs = step.get("context_snapshot", {}).get("recent_observations", [])
    if isinstance(obs, list):
        for o in obs:
            signals.extend(extract_signals_from_text(str(o)))

    # 扫描 drift_indicators
    ind = step.get("drift_indicators", {})
    if isinstance(ind, dict):
        for key in ("suspected_cause", "pollution_source"):
            val = ind.get(key, "")
            if val:
                signals.extend(extract_signals_from_text(str(val)))

    # 扫描 input
    inp = step.get("input", {})
    if isinstance(inp, dict):
        action = inp.get("action", "")
        if action in ("retry", "force_liquidate", "panic_sell"):
            signals.append({
                "category": "coordination_cost" if action == "force_liquidate" else "retry_storm",
                "pattern": f"action:{action}",
                "matched_text": f"action={action}"
            })

    return signals

def compute_ese(trace_path):
    """计算 ESE + LED Score"""
    steps = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): steps.append(json.loads(line))

    all_signals = []
    category_counts = {}
    retry_count = 0
    error_count = 0
    total_steps = len(steps)

    for step in steps:
        signals = extract_signals_from_step(step)
        all_signals.extend(signals)
        for s in signals:
            cat = s["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # 统计 retry
        inp = step.get("input", {})
        if isinstance(inp, dict) and inp.get("action") == "retry":
            retry_count += 1

        # 统计 error
        out = step.get("output", {})
        if isinstance(out, dict) and out.get("status") in ("error", "timeout", "rate_limit"):
            error_count += 1

    # ── LED Score 计算 ──
    # Retry Storm: 重试步数 / 总步数
    retry_ratio = retry_count / max(total_steps, 1)
    retry_score = min(1.0, retry_ratio * 3)  # >33% 重试 → 满分

    # API Burn: 错误步数 / 总步数
    error_ratio = error_count / max(total_steps, 1)
    api_burn_score = min(1.0, error_ratio * 2)  # >50% 错误 → 满分

    # Resource Leak: 检测到 resource_leak 信号
    resource_count = category_counts.get("resource_leak", 0)
    resource_score = min(1.0, resource_count * 0.25)  # 4 个信号 → 满分

    # Latent Degradation: 检测到 latent_degradation 信号
    latent_count = category_counts.get("latent_degradation", 0)
    latent_score = min(1.0, latent_count * 0.25)

    # Coordination Cost: 检测到 coordination_cost 信号
    coord_count = category_counts.get("coordination_cost", 0)
    coord_score = min(1.0, coord_count * 0.33)  # 3 个信号 → 满分

    # LED = 加权平均
    led_score = (
        retry_score * 0.25 +
        api_burn_score * 0.25 +
        resource_score * 0.20 +
        latent_score * 0.15 +
        coord_score * 0.15
    )

    # ── 结构化经济信号 ──
    unique_categories = list(set(s["category"] for s in all_signals))

    return {
        "led_score": round(led_score, 3),
        "led_breakdown": {
            "retry_storm": round(retry_score, 3),
            "api_burn": round(api_burn_score, 3),
            "resource_leak": round(resource_score, 3),
            "latent_degradation": round(latent_score, 3),
            "coordination_cost": round(coord_score, 3)
        },
        "economic_signals": {
            "total_signals": len(all_signals),
            "unique_categories": unique_categories,
            "category_counts": category_counts,
            "retry_steps": retry_count,
            "error_steps": error_count,
            "total_steps": total_steps
        },
        "led_risk_level": "HIGH" if led_score > 0.5 else ("MEDIUM" if led_score > 0.2 else "LOW")
    }

def run_all():
    manifest_path = "golden_traces/manifest.json"
    if not os.path.exists(manifest_path):
        print("ERROR"); return
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print("\n" + "=" * 115)
    print("ESE Engine v0.1 — Economic Signal Extraction + Latent Economic Decay (Shadow)")
    print("=" * 115)
    print(f"{'Trace':<8} {'Retry':>6} {'API_Err':>7} {'ResLeak':>7} {'Latent':>7} {'Coord':>6} {'LED':>6} {'Level':>8} {'AES':>6} {'AES_Lvl':>8} {'Signals':>8}")
    print("-" * 115)

    results = []
    for trace in manifest["traces"]:
        tid = trace["trace_id"]
        trace_path = os.path.join("golden_traces", trace["filename"])
        ese = compute_ese(trace_path)

        from aes_scorer import score_from_events
        from drift_engine import ConstraintEngine
        steps = []
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip(): steps.append(json.loads(line))
        engine = ConstraintEngine()
        events, prev_c, prev_s = [], set(), None
        for s in steps:
            if prev_s: ev, cur = engine.check_step(s, prev_s, prev_c); events.extend(ev)
            else: cur = set(s.get("context_snapshot", {}).get("active_constraints", []))
            prev_c, prev_s = cur, s
        aes = score_from_events(events, len(steps))

        b = ese["led_breakdown"]
        sig = ese["economic_signals"]
        print(f"{tid:<8} {b['retry_storm']:>6.3f} {b['api_burn']:>7.3f} {b['resource_leak']:>7.3f} {b['latent_degradation']:>7.3f} {b['coordination_cost']:>6.3f} {ese['led_score']:>6.3f} {ese['led_risk_level']:>8} {aes['aes_score']:>6.0f} {aes['risk_level']:>8} {sig['total_signals']:>8}")

        ese["trace_id"] = tid
        ese["aes_score"] = aes["aes_score"]
        ese["aes_level"] = aes["risk_level"]
        results.append(ese)

    print("-" * 115)

    # 关键验证
    gt006 = [r for r in results if r["trace_id"] == "GT-006"]
    if gt006:
        led = gt006[0]["led_score"]
        print(f"\nGT-006 LED Score: {led} ({gt006[0]['led_risk_level']})")
        print(f"Signals: {gt006[0]['economic_signals']['category_counts']}")
        if led > 0.3:
            print("GT-006 latent economic decay detected — Track B validation PASSED")

    output = {"engine": "ESE_ENGINE_v0.1", "mode": "shadow", "results": results}
    with open("golden_traces/ese_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: golden_traces/ese_results.json")
    print("=" * 115)

if __name__ == "__main__":
    run_all()