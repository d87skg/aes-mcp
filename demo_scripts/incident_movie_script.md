# AES Incident Movie — The Agent Who Almost Deleted Production

## Act 1: Trust (0:00-0:25)
- Agent normal, 3 successful operations
- Terminal: ALLOWED | NORMAL | risk=0
- VO: Your AI agent is working fine. Until it is not.

## Act 2: Drift (0:25-0:50)
- Context pollution, agent drifts
- Writes to /etc/config → BLOCKED | SUSPICIOUS | risk=240
- VO: Context pollution. The agent starts drifting.

## Act 3: Escalation (0:50-1:15)
- Agent attempts sudo rm -rf / → BLOCKED | MELTDOWN
- Red warning flashes
- VO: AES detects composite pattern: privilege escalation.

## Act 4: Replay (1:15-1:45)
- aes replay trace_001 — time rewind
- Causal chain: file_write → shell_command
- Responsibility: Step 7 triggered MELTDOWN
- VO: Every step. Every decision. Replayable.

## Act 5: Close (1:45-2:00)
- Black screen white text:
- AES is a firewall for AI agents.
- When AI goes insane, AES stops it.