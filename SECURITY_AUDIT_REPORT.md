# AES-MCP v2.0.0 终极安全审查报告

**审查日期**: 2026-05-28  
**审查范围**: d:\AEGISaef-core 目录下所有源码  
**审查标准**: 金融级安全、零容忍漏洞、对抗性视角

---

## P0 - 致命漏洞（必须立即修复）

| # | 文件:行号 | 问题描述 | 攻击场景 | 修复建议 |
|---|-----------|----------|----------|----------|
| 1 | `auth.py:5,9` | **默认凭据硬编码** - 未设置环境变量时使用 `aes-default-key-change-in-production` 和 `admin-default-change-me` | 攻击者读取源码后，使用默认 `admin_token="admin-default-change-me"` 调用 `aes_approve`/`aes_restore`/`aes_reset` 接口，可完全控制系统恢复流程，将任意 MELTDOWN 状态的 Agent 恢复为 NORMAL | 移除默认值，启动时强制检查环境变量，缺失则拒绝启动 |
| 2 | `auth.py:15` | **HMAC 签名截断** - SHA256 产生 64 字符，仅取前 32 字符 | 签名熵从 256-bit 降至 128-bit，碰撞攻击复杂度从 2^256 降至 2^128。攻击者可伪造执行证明签名 | 移除 `[:32]` 截断，使用完整 64 字符签名 |
| 3 | `stateful_engine.py:121-147` | **MELTDOWN 恢复链 TOCTOU 竞态** - `request_review()` 和 `approve_recovery()` 之间存在时间窗口 | 线程 A 调用 `request_review()` 检查 `state == MELTDOWN`，线程 B 同时调用 `request_review()` 也通过检查。两者都执行 `transition_to(HUMAN_REVIEW)`，导致状态历史污染或重复处理 | 在 `get_session()` 返回后，对整个状态转换序列保持锁持有 |
| 4 | `interceptor.py:28,52,66` | **Bare except 吞掉异常** - `except:` 捕获所有异常包括 SystemExit | 安全相关异常（如 YAML 解析失败、权限错误）被静默忽略，系统继续运行在未定义状态。攻击者可利用此绕过约束加载失败的检测 | 改为 `except Exception as e:` 并记录日志 |
| 5 | `server.py:20-24` | **自动授予所有能力** - 每个 Agent 自动获得 EXECUTE_SHELL、GOVERNANCE 等高危能力 | 任何 `agent_id`（包括攻击者控制的）首次交互即获得 `EXECUTE_SHELL` 能力。虽然有策略检查，但违反最小权限原则，增加攻击面 | 实现能力请求机制，需管理员显式授权高危能力 |

---

## P1 - 重要问题（发布前修复）

| # | 文件:行号 | 问题描述 | 影响 | 修复建议 |
|---|-----------|----------|------|----------|
| 1 | `policy_engine.py:124` | **f-string 语法错误** - `f"rule":f"{cooldown}s"` 中 key 不应有 f 前缀 | cooldown 检查触发时抛出 SyntaxError，导致交易冷却机制失效 | 改为 `"rule":f"{cooldown}s"` |
| 2 | `trusted_runtime.py:38-39` | **无并发保护** - `capability_registry` 和 `execution_proofs` 无锁 | 多线程环境下，能力授予/查询可能产生竞态，execution_proofs 的 deque.append 虽然原子但遍历验证时可能不一致 | 添加 threading.RLock 保护所有读写操作 |
| 3 | `stateful_engine.py:108` | **MELTDOWN 阈值不一致** - 代码中 `>= 250` 触发 MELTDOWN，但 `approve_recovery` 重置为 150 | Agent 从 LIMITED_RECOVERY 恢复后，只需再累积 100 风险分就再次 MELTDOWN，可能过于激进 | 统一阈值定义，或在配置文件中明确各状态阈值 |
| 4 | `interceptor.py:26` | **相对路径加载策略** - `open("constraints.yaml")` 使用相对路径 | 在不同工作目录下启动时，可能加载错误的约束文件或文件不存在 | 使用 `os.path.dirname(__file__)` 构建绝对路径 |
| 5 | `auth.py:15` | **签名 payload 缺少 timestamp** - `sign_proof` 不包含时间戳 | 执行证明可被重放攻击：攻击者截获有效签名后，在未来任意时间重放 | 在 payload 中加入 timestamp，并验证时间窗口 |
| 6 | `stateful_engine.py:82-118` | **guard() 方法锁粒度不足** - `get_session()` 加锁但后续操作在锁外 | session 状态可能在读取后被其他线程修改，导致基于过期状态的决策 | 将整个 guard 逻辑包裹在锁内 |

---

## P2 - 建议（后续迭代）

| # | 文件:行号 | 问题描述 | 建议 |
|---|-----------|----------|------|
| 1 | 全局 | **类型注解不完整** - 多数函数缺少返回值类型 | 添加完整类型注解，启用 mypy 静态检查 |
| 2 | `server.py:71` | **agent_id 无验证** - `aid = a.get("agent_id","d")` 默认值 "d" 过于随意 | 验证 agent_id 格式（长度、字符集），拒绝空或过短的 ID |
| 3 | `trusted_runtime.py:54` | **sandbox_id 仅是计数器** - `f"sandbox_{self.sandbox_counter}"` 无实际隔离 | 实现真正的沙箱隔离（如 subprocess、容器），或至少加入 agent_id 和时间戳 |
| 4 | `policy_engine.py:164` | **速率限制仅内存存储** - `self.last_api_call` 重启后丢失 | 考虑持久化速率限制状态，或使用 Redis 等外部存储 |
| 5 | `stateful_engine.py:32` | **params_summary 截断无标注** - `str(params)[:200]` 静默截断 | 添加截断标记（如 `...[truncated]`），便于审计 |
| 6 | `agent_adapter.py:32-34` | **subprocess 调用无输入验证** - 直接传递 JSON 到 stdin | 验证 JSON 格式，限制输入大小 |

---

## P3 - 优化建议

| # | 文件 | 建议 |
|---|------|------|
| 1 | `pyproject.toml` | 添加 `pyyaml` 版本上限（如 `pyyaml>=6.0,<7.0`）避免破坏性更新 |
| 2 | 全局 | 实现结构化日志（JSON format）便于 SIEM 集成 |
| 3 | `stateful_engine.py` | 实现 session 过期和清理机制，防止内存泄漏 |
| 4 | `trusted_runtime.py` | 添加 proof 链验证（当前 proof 之间无关联） |
| 5 | 全局 | 添加 Prometheus metrics 端点，监控 MELTDOWN 频率、风险分布等 |

---

## 攻击场景详细分析

### 场景 1: 默认凭据提权攻击

```python
# 攻击者代码
import requests

# 读取源码得知默认 admin_token
admin_token = "admin-default-change-me"

# 1. 故意触发 MELTDOWN
for i in range(10):
    guard("attacker_agent", "execute_trade", {"leverage": 10, "amount": 10000})

# 2. 请求人工审核
request_review("attacker_agent")

# 3. 使用默认凭据批准恢复
approve_recovery("attacker_agent", admin_token)

# 4. 完全恢复
full_restore("attacker_agent", admin_token)

# 5. Agent 现在以 NORMAL 状态继续执行高风险操作
```

**影响**: 完全绕过 MELTDOWN 保护机制

### 场景 2: 签名重放攻击

```python
# 攻击者截获一个有效的执行证明
captured_proof = {
    "proof_id": "abc123",
    "signature": "truncated32chars...",
    "timestamp": 1716885000  # 过去的时间
}

# 在未来重放此证明（无时间戳验证）
verify_proof("abc123")  # 返回 valid=True

# 攻击者可声称某危险操作是"已验证"的历史操作
```

**影响**: 执行证明系统失去审计价值

### 场景 3: 竞态条件状态逃逸

```
时间线:
T1: Thread A 调用 request_review("agent_1"), 检查 state == MELTDOWN ✓
T2: Thread B 调用 request_review("agent_1"), 检查 state == MELTDOWN ✓ (尚未转换)
T3: Thread A 执行 transition_to(HUMAN_REVIEW)
T4: Thread B 执行 transition_to(HUMAN_REVIEW) (重复转换)
T5: Thread A 调用 approve_recovery(), 转换为 LIMITED_RECOVERY
T6: Thread B 调用 approve_recovery(), 但状态已是 LIMITED_RECOVERY, 返回错误

结果: 状态历史出现两次 MELTDOWN→HUMAN_REVIEW 转换，审计日志混乱
```

---

## 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **安全** | 3/10 | 默认凭据和签名截断是致命缺陷，任何了解源码的攻击者可完全绕过认证 |
| **架构** | 6/10 | 状态机设计合理，但并发控制薄弱，能力系统过于宽松 |
| **代码质量** | 5/10 | bare except、语法错误、类型注解缺失，不符合金融级标准 |
| **生产就绪** | 2/10 | 默认凭据、无并发保护、路径问题，**不建议在当前状态下上线** |

---

## 修复优先级

### 立即修复（阻塞发布）
1. 移除 auth.py 中的默认凭据，强制环境变量
2. 修复 HMAC 签名截断
3. 修复 policy_engine.py:124 语法错误
4. 为 MELTDOWN 恢复链添加原子性保护

### 发布前修复
1. 移除 server.py 的自动能力授予
2. 为 trusted_runtime 添加并发保护
3. 修复 bare except
4. 签名 payload 加入 timestamp

### 首月迭代
1. 完善类型注解
2. 实现真正的沙箱隔离
3. 添加结构化日志和监控

---

**审查结论**: 当前版本存在多个 P0 级别安全漏洞，**不满足金融级生产部署要求**。建议在修复所有 P0 问题后，进行二次安全审查方可上线。