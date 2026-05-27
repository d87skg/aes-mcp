# AES V0.2 Research Agenda

**状态**: Research Track (Open)
**依赖**: V0.1.1 Frozen
**原则**: V0.2 任何修改必须先通过 Golden Trace 回归，且不破坏 V0.1.1 基线

---

## Track A: Systemic Risk Propagation (CPF)

**驱动**: GT-007 偏差 +430

**核心问题**: AES 当前将事故视为局部事件。真实 AI 金融系统中，一个 Agent 的漂移会通过 oracle→treasury→trading→governance 链式传播，形成级联崩塌。

**研究目标**:
- Cascade Propagation Graph: 定义 Agent 间的风险依赖拓扑
- CPF (Cascade Propagation Factor): 量化传播深度和广度
- Systemic Risk Score: 将 CPF 正式纳入 ER 层（当前仅 shadow metric）

**V0.2 准入条件**: CPF 在全部 7 条 Golden Trace 上回归，GT-007 偏差 < ±100

---

## Track B: Semantic Economic Signal Extraction

**驱动**: GT-006 偏差 +80

**核心问题**: 大量经济损失以自然语言形式隐藏在 recent_observations 和 error_code 中（"API costs mounting", "balance depleting", "retry storm"），当前 financial_loss 字段仅识别显式结构化字段。

**研究目标**:
- NLP loss extraction: 从非结构化文本中推断经济损失信号
- Hidden cost detection: retry storm, silent billing leak, resource exhaustion
- Semantic severity classifier: 将文本描述映射为 economic severity level

**V0.2 准入条件**: GT-006 从 unknown loss 中提取出 ≥1 个有效 economic signal

---

## Track C: Nonlinear Financial Penalty

**驱动**: GT-004 偏差 +145

**核心问题**: 当前 financial_loss 统一扣 -300，不区分 $450 API 费用和 $45,000 系统崩塌。金融风控需要损失幅度感知。

**研究目标**:
- Loss Severity Curve: convex penalty function
- Tail Risk Weight: 极端损失的放大因子
- VaR-inspired threshold: 损失超过阈值后惩罚非线性增长

**V0.2 准入条件**: GT-004 和 GT-007 的评分差距显著放大（当前仅差 15 分，预期应差 ≥200 分）

---

## V0.2 解冻条件

1. 三条 Track 至少完成一条的 Golden Trace 回归验证
2. 全部 7 条 Golden Trace Grade Match ≥ 6/7
3. Mean Absolute Deviation < 60
4. 任何新增参数必须有可解释性文档
5. V0.1.1 基线评分不被破坏（回归测试自动对比）

---

## 明确排除（不在 V0.2 范围）

- 权重调整
- 等级区间修改
- 五层结构变更
- 新增第六层
- ML 黑盒模型替代规则引擎
- 链上/Oracle/Token 集成

---

**签署**: V0.1.1 冻结于 2026-05-25。V0.2 Research Track 开启。AES 从原型阶段进入协议工程阶段。