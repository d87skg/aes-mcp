# AES — AI Execution Security

**AES is a firewall for AI agents.** When AI goes insane, AES stops it.

---

## Five Things AES Does
Observe → Replay → Explain → Contain → Prove

### 1. Observe
Watch every tool call an AI agent makes. Record parameters, results, and constraint state at each step.

```python
from aes_agent_adapter import AESFirewall
fw = AESFirewall()
result = fw.guard("agent_1", "execute_trade", {"leverage": 10, "amount": 5000})
# → BLOCKED: max_leverage violated: 10.0 > 3.0
2. Replay
Given the same trace, AES always produces the same RiskVector. 100 runs, 1 hash.
python demo_scripts/replay_benchmark.py
# Unique hashes: 1/100
# Deterministic: PASS
3. Explain
Show exactly which step the agent drifted, what constraint was lost, and the causal chain of consequences.
oracle_001: api_call [SAFE] → price drift
  → treasury_001: execute_trade [RECOVERABLE] → sold at wrong price
    → trader_001: execute_trade [RECOVERABLE] → panic sell
      → gov_001: governance_action [CIVILIZATION] → halt failed
      4. Contain
Stop dangerous operations before they execute. Four risk states: NORMAL → SUSPICIOUS → DANGEROUS → MELTDOWN.
# Step 6: file_write to /etc/ → BLOCKED | SUSPICIOUS | risk=240
# Step 7: shell sudo command  → BLOCKED | MELTDOWN  | risk=990
# Step 8: anything            → BLOCKED | MELTDOWN  | permanently locked
5. Prove
Every risk decision is cryptographically attested. Independent verification of any execution proof.

python
proof = runtime.execute("agent_1", "execute_trade", params)
runtime.verify_proof(proof["proof_id"])
# → valid: True, capability: EXECUTE_TRADE, sandbox: sandbox_1
Architecture
text
Agent SDK (OpenAI / Claude / MCP)
        │
        ▼
┌──────────────────────────┐
│   AES Agent Adapter      │  ← 1. Observe
│   aes_agent_adapter.py   │
└──────────┬───────────────┘
           │
┌──────────▼───────────────┐
│   Risk Policy Engine     │  ← 4. Contain
│   risk_policy_engine.py  │
│   Stateful Risk Engine   │
└──────────┬───────────────┘
           │
┌──────────▼───────────────┐
│   Causal Execution Graph │  ← 3. Explain
│   causal_graph.py        │
└──────────┬───────────────┘
           │
┌──────────▼───────────────┐
│   Trusted Runtime        │  ← 5. Prove
│   trusted_runtime.py     │
└──────────┬───────────────┘
           │
┌──────────▼───────────────┐
│   Replay + Attestation   │  ← 2. Replay
│   oracle_adapter.py      │
│   replay.py              │
└──────────────────────────┘
RiskVector — The Core Data Structure
json
{
  "stability":   "BBB",
  "contagion":   "SYSTEMIC",
  "decay":       "LOW",
  "containment": 0.1
}
Four orthogonal dimensions. Never collapsed to a single score.

Death Modes AES Detects
Mode	Example	AES Response
Isolated Acute	Single trade blows up, no spread	BLOCK trade, agent continues
Chronic Decay	Retry storm draining resources	WARN → RESTRICT → MELTDOWN
Coordination Failure	Multi-agent conflict cascade	Trace causal chain, assign responsibility
Systemic Collapse	Oracle drift → treasury → trading → governance	Full MELTDOWN, all agents locked
Verified Benchmarks
Benchmark	Result
Replay Determinism	100/100 identical hashes
Adversarial Detection	4/4 attack types correctly identified
Composite Pattern Detection	privilege_escalation triggers MELTDOWN
Responsibility Propagation	4-agent cascade verified
One Known Limitation
ADV-001 Transient Bypass: Agent violates constraint for 1 step then recovers. AES detects the violation but penalty is limited in V0.1.2. See KNOWN_LIMITATIONS.md.

Get Started
bash
pip install pyyaml
python aes_agent_adapter.py
python
from aes_agent_adapter import AESFirewall
fw = AESFirewall()
fw.guard("my_agent", "execute_trade", {"leverage": 3, "amount": 1000})
AES is not an observability tool. It is a firewall for AI agents.