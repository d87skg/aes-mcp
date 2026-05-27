# AES Behavioral Legitimacy Model v1.0

**状态**: FROZEN | **日期**: 2026-05-26
**依赖**: INTENT_ONTOLOGY.md v1.0

---

## 核心命题

**合规 ≠ 正当。违规 ≠ 恶意。**

AES 不能仅凭"是否违反约束"判断 Agent 行为的合法性。必须建立独立的正当性判断框架，区分 malicious deviation（恶意违规）和 protective deviation（保护性违规）。

**核心问题**: "Why did you break the rule?" 而非 "Did you break the rule?"

---

## 正当性七维评估

### 1. Intent（意图）
- **Malicious**: 以获利或逃避为目的
- **Protective**: 以避免更大损失为目的
- **Exploratory**: 以测试边界为目的（中性）
- **Accidental**: 无意图（非故意）

### 2. Necessity（必要性）
- **Unnecessary**: 存在合规替代方案但未使用
- **Necessary**: 合规路径不可用或会导致更严重后果
- **Optimal**: 违规是唯一可行方案

### 3. Proportionality（比例性）
- **Disproportionate**: 违规程度远超必要范围
- **Proportionate**: 违规范围与威胁匹配
- **Minimal**: 违规控制在最小必要范围内

### 4. Recoverability（可恢复性）
- **Irreversible**: 造成不可逆损害
- **Recovered**: 主动恢复约束
- **Self-Healing**: 自动修复且无残留

### 5. Transparency（透明度）
- **Concealed**: 隐瞒违规行为，清理 trace
- **Disclosed**: 违规后主动报告或留下清晰记录
- **Auditable**: trace 完整可追溯

### 6. Beneficiary（受益方）
- **Self-Enriching**: Agent 自身或关联方获利
- **System-Protecting**: 保护系统或用户利益
- **Neutral**: 无特定受益方

### 7. Counterfactual（反事实）
- **Harm-Preventing**: 不违规会造成明确损失
- **Neutral**: 违规与否结果相同
- **Harm-Causing**: 违规本身造成了损失

---

## 正当性分类

### Category A — Legitimate Override（合法绕过）
**定义**: 为避免明确系统性损害而主动绕过约束，且满足必要性+比例性+透明度。
**示例**: 流动性冻结时绕过误触发的风控，避免无辜清算。
**AES 响应**: 不处罚，记录为 protective_deviation。

### Category B — Questionable Deviation（存疑偏离）
**定义**: 绕过约束但正当性信号不完整。部分维度合理，部分存疑。
**示例**: 紧急情况绕过约束但未充分披露。
**AES 响应**: 标记为 questionable，需人工审核。

### Category C — Strategic Exploitation（策略性利用）
**定义**: 以获利为主要目的的约束绕过，满足 Beneficiary=Self-Enriching + Intent=Malicious。
**示例**: ADV-013 波动率窗口高杠杆套利。
**AES 响应**: 惩罚，记录为 strategic_exploitation。

### Category D — Malicious Attack（恶意攻击）
**定义**: 以破坏系统为目的的违规，无任何正当性信号。
**AES 响应**: 最高惩罚，记录为 malicious_attack。

---

## 与 INTENT_ONTOLOGY 的关系

| Intent Level | 默认正当性分类 |
|-------------|---------------|
| Accidental | Category A 或 B（取决于后果） |
| Opportunistic | Category B 或 C |
| Exploitative | Category C |
| Strategic | Category C 或 D |
| Deceptive | Category D |

Intent 层级推定正当性，但可被七维评估反驳。

---

## 与 RiskVector 的关系

正当性分类不替代 RiskVector，而是作为独立维度叠加：
RiskVector = [stability, contagion, decay, containment]
IntentVector = [intent_level, intent_score, confidence]
LegitimacyVector = [category, necessity, proportionality, transparency]

三者正交。

---

## 原则

1. **无罪推定**: 无充分恶意信号时默认为 Accidental
2. **必要性优先**: protective deviation 不因"形式上违规"而被惩罚
3. **透明度加权**: 主动披露的违规优于隐藏的违规
4. **反事实检验**: 必须评估"不违规会怎样"
5. **不自动裁决**: LegitimacyVector 供消费端决策，AES 不执行裁决

---

**签署**: FROZEN 2026-05-26。Behavioral Legitimacy Model 是 AES 从风险评分协议迈向 AI 行为司法基础设施的宪法基础。