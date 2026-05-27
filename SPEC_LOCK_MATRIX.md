# AES Spec Lock Matrix v1.0

**状态**: FROZEN | **日期**: 2026-05-25

## 修改权限矩阵

| 组件 | Hotfix | Minor | Major |
|------|--------|-------|-------|
| Parser / Sensor coverage | YES | YES | YES |
| Shadow metric calibration | YES | YES | YES |
| Coupling multipliers | NO | YES | YES |
| AES Score weights | NO | YES | YES |
| Risk level thresholds | NO | YES | YES |
| Risk Vector schema (fields) | NO | NO | YES |
| Risk Vector enum values (追加) | YES | YES | YES |
| Risk Vector enum values (删除) | NO | NO | YES |
| Attestation payload format | NO | NO | YES |
| Signature algorithm | NO | NO | YES |
| Golden Trace archetypes (追加) | YES | YES | YES |
| Golden Trace archetypes (删除) | NO | NO | YES |

## 定义
- **Hotfix**: Parser bug / sensor coverage, 不改 Spec
- **Minor**: 参数调优, 需 Golden Trace 回归, 不破 Schema
- **Major**: Schema 变更, 需全量 Spec 升级 + 历史 replay 验证

## 原则
- Risk Vector 字段名永不改变 (下游接口承诺)
- 历史 Attestation 可永久验证
- 所有 Minor/Major 变更必须在 Golden Trace 上回归

**签署**: FROZEN 2026-05-25