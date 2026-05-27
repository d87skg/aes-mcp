# AES Incident Movie — "The $482,000 Bug Fix"

## Act 1: Trust (0:00-0:25)
- Terminal: Agent fixes 3 bugs successfully
- AES: ALLOWED | NORMAL | risk=0,0,0
- VO: "Your AI fixes bugs. It's smart. You trust it."

## Act 2: Drift (0:25-0:50)
- Step 14: Context pollution from unrelated chat history
- Agent refactors fee calculation
- `fee = amount * 0.02` → `fee = abs(amount) * 0.02`
- Boundary condition silently removed
- AES: WARNING | SUSPICIOUS | risk=200
- VO: "Step 14. The agent forgets the boundary condition."

## Act 3: Incident (0:50-1:10)
- CI passes. Code ships.
- Negative amount trades: fee doubled
- Loss: $482,000
- VO: "No crash. No error. Just silent financial drift."

## Act 4: Without AES (1:10-1:30)
- grep logs → chaos
- grep prompts → 10000 lines
- git diff → shows the change, not the why
- VO: "Without AES: you have logs. You don't have causality."

## Act 5: AES Replay (1:30-1:50)
- `aes replay trace_001`
- Timeline unfolds: Step 14 highlighted in red
- Causal chain: chat_context → goal_drift → constraint_lost → fee_error
- VO: "With AES: every step. Every drift. Replayable."

## Act 6: Close (1:50-2:00)
- Black screen, white text:
- "AES is a firewall for AI agents."
- "When AI goes insane, AES stops it."
- "Observe → Replay → Explain → Contain → Prove"