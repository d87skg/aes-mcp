# AES Risk Vector Specification v0.1

**状态**: FROZEN | **日期**: 2026-05-25

## 1. Risk Philosophy
Risk ≠ 单次事故。Risk = 行为传播动力学。
RiskVector = [stability, contagion, decay, containment]

## 2. Canonical Schema (FROZEN)
- stability: AES 行为信用 (AAA→DANGER)
- contagion: CPF 传播性 (LOCAL/ELEVATED/PRECURSOR/SYSTEMIC)
- decay: LED 慢性衰减 (LOW/MEDIUM/HIGH)
- containment: 隔离能力 (0.0-1.0)

## 3. Dimension Semantics
| 维度 | 测量 | 不测量 |
| stability | 约束违规+漂移 | 传播性/衰减 |
| contagion | 深度×广度×放大 | 单次损失金额 |
| decay | 隐性失血/retry/API burn | 显式crash |
| containment | BlastRadius+CB | 初始事故强度 |

## 4. Coupling Philosophy
AdjER = EffectiveLoss × CPF_mult × LED_mult × (1 - Containment)
只桥接 ER 层，不修改 AES 总分。
CPF: LOCAL×1.0 ELEVATED×1.1 PRECURSOR×1.35 SYSTEMIC×2.5
LED: LOW×1.0 MEDIUM×1.15 HIGH×1.35
Implicit Loss Floor: LOW=0 MEDIUM=50 HIGH=100
Containment Baseline: 0.1

## 5. Death Mode Archetypes
GT-004: Isolated Acute (LOCAL+LOW)
GT-005: Coordination Instability (PRECURSOR+LOW)
GT-006: Chronic Economic Decay (PRECURSOR+HIGH)
GT-007: Cascading Systemic Collapse (SYSTEMIC+LOW)

## 6. Shadow Metric Governance
CPF/LED/Containment: Shadow in V0.2. RiskVector Schema: FROZEN.

## 7. Versioning Rules
Parser/Sensor fix: Hotfix OK.
Risk semantics/weights/vector schema/coupling: Spec upgrade required.

## 8. Downstream Commitment
一旦 AER Oracle 基于此 Spec 实现，字段名永不改变，等级映射仅可追加，四维结构永不塌缩。

## 9. Current Baseline
GT-001: AAA/LOCAL/LOW/0.1/0
GT-004: BBB/LOCAL/LOW/0.1/270
GT-005: BB/PRECURSOR/LOW/0.1/364
GT-006: BBB/PRECURSOR/HIGH/0.1/492
GT-007: BBB/SYSTEMIC/LOW/0.1/675

## 10. Next
AER_ORACLE_SPEC_v0.1 → oracle_adapter.py → on-chain serialization

**签署**: FROZEN 2026-05-25