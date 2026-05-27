# CPF Specification v0.1 — Cascade Propagation Factor

**状态**: Research Track A (Open)
**依赖**: AES_SCORE_SPEC_v0.1.1 (Frozen)

## 1. 核心定义
CPF = Depth x Breadth x Amplification x (1 + Containment_Failure)

## 2. 四个维度
- Propagation Depth: 穿透系统层数 (1.0-4.0+)
- Propagation Breadth: 受影响独立模块数 (1.0-4.0+)
- Economic Amplification: Loss_final / Loss_initial (1.0-5.0+)
- Containment Failure: 隔离失败程度 (0-2.0)

## 3. 等级
LOCAL(1.0-1.5) | REGIONAL(1.5-3.0) | SYSTEMIC(3.0-6.0) | CASCADING(6.0+)

## 4. GT-007 验证
Depth=4, Breadth=4, Amplification=7.5x, Containment=2.0 → CPF=144.0 CASCADING
