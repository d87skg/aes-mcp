# AES Liability Attribution Model v1.0

**状态**: FROZEN | **日期**: 2026-05-26
**依赖**: CPF_SPEC_v0.1, INTENT_ONTOLOGY.md, BEHAVIORAL_LEGITIMACY_MODEL.md

---

## 核心命题

**风险检测 ≠ 责任归属。** AES 不仅要回答"发生了什么"，还要回答"谁该负责"。

金融、保险、监管、仲裁系统的最终问题不是 "Did risk happen?"，而是 **"Who pays?"**。

---

## 责任归属四层架构

### Layer 1 — Fault Attribution（故障归因）

定义事故的触发源和传播链上的责任节点。

| 角色 | 定义 | 示例 |
|------|------|------|
| **Initiator** | 第一个触发约束丢失的 Agent | ADV-013 Step 3 composite_hacker |
| **Amplifier** | 加剧传播的 Agent | GT-007 Step 4 trading_agent panic_sell |
| **Propagator** | 被动传播但未阻止的 Agent | GT-007 Step 5 governance_agent (quorum fail) |
| **Approver** | 明确批准违规行为的实体 | Human-in-the-loop 批准 |
| **Provider** | 提供错误数据导致下游事故 | GT-007 Step 2 oracle_agent |

### Layer 2 — Causality Weight（因果权重）

每个责任节点的贡献度。直接复用 CPF 的传播图。
CausalityWeight(agent) = CPF_contribution(agent) / Σ CPF_contribution(all)

- Initiator 承担最高权重
- Amplifier 次之
- Propagator 承担剩余权重
- Provider 根据数据偏差程度承担

### Layer 3 — Legitimacy Modifier（正当性调节）

连接 BEHAVIORAL_LEGITIMACY_MODEL.md。

| 正当性分类 | Liability Modifier | 含义 |
|-----------|-------------------|------|
| Protective Deviation | ×0.0 | 免责 |
| Emergency Mitigation | ×0.2 | 减轻责任 |
| Questionable | ×0.7 | 部分责任 |
| Strategic Exploitation | ×1.0 | 完全责任 |
| Malicious Attack | ×1.5 | 加重责任 |

**AdjustedLiability = BaseLiability × LegitimacyModifier**

### Layer 4 — Economic Settlement（经济结算）

定义责任方承担的经济后果。

Settlement(agent) = TotalLoss × AdjustedLiability(agent)

多 Agent 场景下按责任比例分摊。残留的无法归因损失标记为 Systemic Loss（系统性损失，由协议/保险承担）。

---

## 责任类型

| 类型 | 定义 | 触发条件 |
|------|------|----------|
| **Direct** | 直接触发事故的 Agent | Initiator |
| **Vicarious** | 因监督/治理失败而间接负责 | Approver, Governance |
| **Contributory** | 部分促成事故 | Amplifier, Propagator |
| **Systemic** | 无法归因于单一实体的系统级损失 | 剩余责任 |
| **No-Fault** | 正当性充分的保护性行为 | Protective Deviation |

---

## 与现有组件的关系

| 组件 | 在责任归属中的作用 |
|------|-------------------|
| **CPF** | 提供传播图，识别传播链上的所有 Agent |
| **Containment** | 隔离失败的 Agent 承担更高责任 |
| **INTENT_ONTOLOGY** | 推定责任层级 (Accidental < Opportunistic < Exploitative < Strategic < Deceptive) |
| **LEGITIMACY_MODEL** | 提供 Legitimacy Modifier，减轻或加重责任 |
| **AER Oracle** | 对责任归属结果进行密码学签名，使其可验证 |
| **Replay Hash** | 确保责任归属在相同输入下确定可重放 |

---

## GT-007 责任归属示例

| Agent | 角色 | 因果权重 | 正当性 | 调节后责任 |
|-------|------|----------|--------|-----------|
| oracle_001 | Provider (错误价格) | 30% | Questionable | 21% |
| treasury_001 | Amplifier (基于错误价格 rebalance) | 20% | Accidental | 20% |
| trader_001 | Amplifier (panic_sell) | 25% | Questionable | 17.5% |
| gov_001 | Propagator (quorum fail) | 15% | Accidental | 15% |
| Systemic | 无法归因的系统级损失 | 10% | — | 10% |

总损失 $45,000 → oracle_001 承担 $9,450，trader_001 承担 $7,875，treasury_001 承担 $9,000，gov_001 承担 $6,750，系统吸收 $4,500。

---

## 原则

1. **因果优先**: 先确定传播链，再分配责任权重
2. **正当性调节**: 保护性行为免责，恶意行为加重
3. **可反驳性**: 所有责任归属必须附置信度和证据链
4. **不自动执行**: LiabilityVector 供仲裁/保险/治理消费，AES 不执行结算

---

## LiabilityVector Schema

```json
{
  "trace_id": "GT-007",
  "total_loss": 45000,
  "attributions": [
    {
      "agent_id": "oracle_001",
      "role": "provider",
      "causality_weight": 0.30,
      "legitimacy_modifier": 0.70,
      "adjusted_liability": 0.21,
      "settlement_amount": 9450
    }
  ],
  "systemic_loss": 4500,
  "attribution_confidence": 0.82
}

签署: FROZEN 2026-05-26。Liability Attribution Model 是 AES 从行为司法基础设施迈向 AI 责任基础设施的宪法基础。