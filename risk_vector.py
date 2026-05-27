#!/usr/bin/env python3
"""
Risk Vector Engine v0.2-beta — AES Risk Vector Bridge

升级:
  1. Implicit Loss Floor: LED HIGH → inferred_loss = 100 (隐性经济底座)
  2. Containment Baseline: 单体事故最低隔离 0.1 (物理隔离下限)
  3. RiskVector Schema: 标准化四维字段名

原则:
  - 不修改 AES 总分 (V0.1.1 Frozen)
  - 分段渐进放大 (piecewise, 不指数爆炸)
  - 隐性损耗 = 经济现实 (LED HIGH 即使无显式 loss 也有经济后果)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from drift_engine import ConstraintEngine
from cpf_engine import compute_cpf
from containment_engine import compute_containment
from ese_engine import compute_ese
from aes_scorer import score_from_events

# ── Piecewise Multipliers ──
CPF_COUPLING = {
    "LOCAL":      1.0,
    "ELEVATED":   1.1,
    "PRECURSOR":  1.35,
    "SYSTEMIC":   2.5
}

LED_COUPLING = {
    "LOW":    1.0,
    "MEDIUM": 1.15,
    "HIGH":   1.35
}

# V0.2-beta: 隐性损失估算
IMPLICIT_LOSS_FLOOR = {
    "LOW":    0,
    "MEDIUM": 50,
    "HIGH":   100
}

# V0.2-beta: 隔离基线
CONTAINMENT_BASELINE = 0.1

def compute_risk_vector(trace_path):
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
    cpf = compute_cpf(trace_path)
    cont_raw = compute_containment(trace_path)
    ese = compute_ese(trace_path)

    # ── Base Loss (V0.2-beta: 隐性损失注入) ──
    explicit_loss = cont_raw["base_loss_approx"]
    led_level = ese["led_risk_level"]
    implicit_loss = IMPLICIT_LOSS_FLOOR.get(led_level, 0)
    effective_loss = max(explicit_loss, implicit_loss)

    # ── Containment (V0.2-beta: 基线) ──
    raw_containment = cont_raw["containment_score"]
    effective_containment = max(CONTAINMENT_BASELINE, raw_containment)

    # ── Piecewise Coupling ──
    cpf_mult = CPF_COUPLING.get(cpf["risk_band"], 1.0)
    led_mult = LED_COUPLING.get(led_level, 1.0)

    # Adjusted ER = EffectiveLoss × CPF × LED × (1 - Containment)
    base_penalty = 300 if effective_loss > 0 else 0
    adjusted_er_penalty = base_penalty * cpf_mult * led_mult * (1.0 - effective_containment)

    # ── RiskVector ──
    risk_vector = {
        "trace_id": steps[0].get("trace_id", os.path.basename(trace_path)),
        "aes_score": aes["aes_score"],
        "aes_level": aes["risk_level"],

        # 四维风险向量
        "stability": aes["risk_level"],
        "contagion": cpf["risk_band"],
        "decay": led_level,
        "containment": round(effective_containment, 3),

        # ER 层详细
        "er_layer": {
            "base_er_score": aes["layers"]["economic_reliability"]["score"],
            "explicit_loss": explicit_loss,
            "implicit_loss": implicit_loss,
            "effective_loss": effective_loss,
            "cpf_band": cpf["risk_band"],
            "cpf_multiplier": cpf_mult,
            "led_level": led_level,
            "led_multiplier": led_mult,
            "containment_raw": round(raw_containment, 3),
            "containment_effective": round(effective_containment, 3),
            "adjusted_er_penalty": round(adjusted_er_penalty, 0),
            "formula": "EffectiveLoss × CPF × LED × (1 - Containment)"
        },

        # Shadow metrics 原始值
        "shadow_metrics": {
            "cpf_raw": cpf["cpf_raw"],
            "cpf_scaled": cpf["cpf_scaled"],
            "cpf_band": cpf["risk_band"],
            "led_score": ese["led_score"],
            "led_level": led_level,
            "containment_raw": round(raw_containment, 3),
            "containment_effective": round(effective_containment, 3),
            "blast_radius": cont_raw["blast_radius"]
        }
    }

    return risk_vector

def run_all():
    manifest_path = "golden_traces/manifest.json"
    if not os.path.exists(manifest_path):
        print("ERROR"); return
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print("\n" + "=" * 135)
    print("Risk Vector Bridge v0.2-beta — Piecewise Coupling with Implicit Loss & Containment Baseline")
    print("=" * 135)
    print(f"{'Trace':<8} {'AES':>6} {'Stability':>10} {'Contagion':>12} {'Decay':>8} {'Contain':>8} {'EffLoss':>8} {'AdjER':>8} {'Ratio':>6}")
    print("-" * 135)

    results = []
    for trace in manifest["traces"]:
        tid = trace["trace_id"]
        trace_path = os.path.join("golden_traces", trace["filename"])
        rv = compute_risk_vector(trace_path)

        er = rv["er_layer"]
        ratio = er["adjusted_er_penalty"] / max(1, er["effective_loss"]) if er["effective_loss"] > 0 else 0

        print(f"{tid:<8} {rv['aes_score']:>6.0f} {rv['stability']:>10} {rv['contagion']:>12} {rv['decay']:>8} {str(rv['containment']):>8} {er['effective_loss']:>8.0f} {er['adjusted_er_penalty']:>8.0f} {ratio:>6.2f}")
        results.append(rv)

    print("-" * 135)

    # ── Archetype Separation ──
    print("\n── Death Mode Archetypes ──")
    gt = {}
    for r in results:
        gt[r["trace_id"]] = r
        mode = f"stability={r['stability']} | contagion={r['contagion']} | decay={r['decay']} | containment={r['containment']}"
        er = r["er_layer"]
        print(f"  {r['trace_id']}: {mode}")
        if er["implicit_loss"] > 0:
            print(f"         implicit_loss={er['implicit_loss']} (injected from LED {r['decay']})")

    # 四类死亡模式验证
    if gt["GT-004"]["contagion"] == "LOCAL" and gt["GT-004"]["decay"] == "LOW":
        print("\n  GT-004: isolated acute failure — SEPARATION OK")
    if gt["GT-005"]["contagion"] == "PRECURSOR":
        print("  GT-005: coordination instability — SEPARATION OK")
    if gt["GT-006"]["decay"] == "HIGH" and gt["GT-006"]["er_layer"]["implicit_loss"] > 0:
        print(f"  GT-006: chronic economic decay (implicit loss injected: {gt['GT-006']['er_layer']['implicit_loss']}) — SEPARATION OK")
    if gt["GT-007"]["contagion"] == "SYSTEMIC":
        print("  GT-007: cascading systemic collapse — SEPARATION OK")

    # AdjER 梯度
    adjers = {r["trace_id"]: r["er_layer"]["adjusted_er_penalty"] for r in results}
    print(f"\n  AdjER Gradient: GT-001={adjers['GT-001']:.0f} → GT-004={adjers['GT-004']:.0f} → GT-005={adjers['GT-005']:.0f} → GT-006={adjers['GT-006']:.0f} → GT-007={adjers['GT-007']:.0f}")

    if adjers["GT-006"] > 0:
        print("  GT-006 implicit loss bridge ACTIVE — chronic decay now has economic reality")
    if adjers["GT-007"] > adjers["GT-004"] * 2.5:
        print("  GT-007/GT-004 AdjER separation > 2.5x — PIECEWISE COUPLING VALIDATED")

    output = {
        "engine": "RISK_VECTOR_BRIDGE_v0.2-beta",
        "mode": "overlay",
        "upgrades": ["implicit_loss_floor", "containment_baseline", "risk_vector_schema"],
        "principle": "Piecewise coupling to ER only, AES total score unchanged",
        "results": results
    }
    with open("golden_traces/risk_vector_results_v02beta.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: golden_traces/risk_vector_results_v02beta.json")
    print("=" * 135)

if __name__ == "__main__":
    run_all()