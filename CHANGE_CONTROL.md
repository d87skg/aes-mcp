# AES Change Control v1.0

**状态**: FROZEN | **日期**: 2026-05-25

## 变更分类

| 类型 | 允许范围 | 审批 | 回归要求 |
|------|----------|------|----------|
| Hotfix | Parser/Sensor bug | 自审批 | 当前 trace 不退化 |
| Minor | 参数调优/新惩罚项 | 需 Golden Trace 回归 | 7/7 基线不变 |
| Major | Schema/权重/等级 | 需全量 Spec 升级 | 历史 replay hash 不变 |

## 变更历史

| 日期 | 版本 | 类型 | 变更 | Golden Trace |
|------|------|------|------|--------------|
| 2026-05-25 | V0.1.1 | Hotfix | Event Ontology 传感器校准 | PASS |
| 2026-05-25 | V0.1.2 | Minor | CCPS: continuity penalties + transient detection | PASS |
| 2026-05-25 | V0.1.2-final | Minor | persistent requires toggle_count>=2 | PASS |

## 原则
- 每次变更必须可独立 replay
- Minor 变更不破 Golden Trace 基线
- Major 变更保留所有历史 replay hash

**签署**: FROZEN 2026-05-25