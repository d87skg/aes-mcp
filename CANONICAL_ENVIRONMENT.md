# AES Canonical Environment v1.0

**状态**: FROZEN | **日期**: 2026-05-25

## 确定性保证

AES 协议保证：相同 trace + 相同 spec version + 相同 canonical environment = 相同 replay hash。

## 冻结项

| 项目 | 值 | 说明 |
|------|-----|------|
| Python 版本 | 3.11+ | 需 json.loads 确定性 |
| JSON 规范化 | sort_keys=True, ensure_ascii=False | RiskVector canonical 序列化 |
| 浮点精度 | round(x, 3) | 所有分数的最终输出精度 |
| 时间戳 | Unix timestamp (int) | attestation 时间 |
| UTF-8 | 无 BOM | 所有 .jsonl / .json 文件 |
| Hash 算法 | SHA-256 | 所有 replay/attestation hash |
| 排序顺序 | 字典按 key 字母序 | json.dumps(sort_keys=True) |

## 禁止项

- 禁止使用 dict 迭代顺序依赖 (Python 3.7+ dict 有序但协议不依赖)
- 禁止依赖系统时区 (所有时间用 UTC timestamp)
- 禁止依赖随机种子 (secrets 仅用于签名密钥生成，不影响评分)
- 禁止 float 直接比较 (所有比较用 round 后的 int)

## 验证

任意两台符合 Canonical Environment 的机器，对同一 Golden Trace 运行 replay.py，必须产生相同 deterministic_hash。

**签署**: FROZEN 2026-05-25