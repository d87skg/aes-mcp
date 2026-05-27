# AER Oracle Specification v0.1

**状态**: FROZEN | **日期**: 2026-05-25

## 1. 核心原则
AER Oracle 是 Risk Attestation Layer（风险证明层），不是 Risk Judgment Layer。
Oracle 只证明某时某刻观测到了什么风险状态，不裁决该 Agent 应被清算/拒绝/降权。

## 2. 三层架构
Layer 1 - Observation: trace events → RiskVector + AdjER (已完成 risk_vector.py)
Layer 2 - Attestation: 签名 + 时间戳 + 不可抵赖 + 可重放 + 可验证
Layer 3 - Consumption: 外部系统自行决定策略，Oracle 不参与

## 3. 双轨制输出
标量轨: aes_score + aes_level (兼容旧系统)
向量轨: 完整 RiskVector + AdjER + attestation (高级系统)

## 4. 签名模型
算法: ECDSA secp256k1 或 EdDSA ed25519
载荷: Keccak256(Canonical RiskVector JSON)
重放保护: timestamp + trace_id 联合唯一

## 5. 威胁模型
伪造 trace → Merkle proof | 重放攻击 → trace_id 防重放 | Oracle 合谋 → 多节点 V0.2

## 6. 实现计划
Phase 1: oracle_adapter.py | Phase 2: 签名+验证 | Phase 3: 链上序列化 | Phase 4: 多节点

**签署**: FROZEN 2026-05-25