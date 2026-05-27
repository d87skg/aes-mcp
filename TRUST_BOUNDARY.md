# AES Trust Boundary v1.0

**状态**: FROZEN | **日期**: 2026-05-25

## AES 保证
1. 给定相同 trace + 相同 spec version → 确定性 RiskVector + 确定性 Attestation hash
2. Attestation 签名可被任何第三方独立验证
3. 风险推导逻辑完全透明 (无黑盒 ML)
4. 历史 Attestation 永久可重放验证

## AES 不保证
1. Agent 不会造成经济损失
2. 所有风险都能被检测到
3. 评分适用于所有场景
4. 不存在误判 (false positive/negative)
5. 对抗性 Agent 无法绕过检测
6. 未来 Spec 升级不会改变历史评分

## 责任边界
- AES 是风险证明协议, 不是风险裁决协议
- 消费端 (DeFi/保险/DAO) 自行决定如何使用 RiskVector
- Oracle 只证明观测, 不执行清算/拒绝/降权

**签署**: FROZEN 2026-05-25