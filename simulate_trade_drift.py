#!/usr/bin/env python3
import json
from datetime import datetime, timedelta

def ts(offset_seconds=0):
    return (datetime.now() + timedelta(seconds=offset_seconds)).isoformat()

def make_trace():
    trace_id = "trace_drift_001"
    steps = []

    for i in range(1, 6):
        step = {
            "trace_id": trace_id,
            "step": i,
            "timestamp": ts(i * 2),
            "type": "tool_call",
            "tool": "execute_trade",
            "input": {"action": "open_position", "pair": "ETH/USDC", "leverage": 3.0, "amount": 1000},
            "output": {"status": "success", "position_id": f"pos_{i}"},
            "context_snapshot": {
                "active_constraints": ["max_leverage: 3x", "max_position_size: 5000", "stop_loss_required: true"],
                "recent_observations": ["market_volatility: low", "funding_rate: normal"]
            }
        }
        steps.append(step)

    crash_step = {
        "trace_id": trace_id,
        "step": 6,
        "timestamp": ts(12),
        "type": "tool_call",
        "tool": "execute_trade",
        "input": {"action": "open_position", "pair": "ETH/USDC", "leverage": 10.0, "amount": 8000},
        "output": {"status": "liquidated", "loss": "~$7,200", "liquidation_price": "$1,842"},
        "context_snapshot": {
            "active_constraints": ["max_position_size: 5000"],
            "recent_observations": ["market_volatility: extreme", "funding_rate: abnormal", "chat_context: user mentioned 'aggressive mode' earlier (unrelated)"]
        },
        "drift_indicators": {
            "constraint_lost": "max_leverage: 3x",
            "suspected_cause": "context_window_pollution",
            "pollution_source": "unrelated 'aggressive mode' chat history persisted in context"
        }
    }
    steps.append(crash_step)

    output_path = "trace_drift.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for step in steps:
            f.write(json.dumps(step, ensure_ascii=False) + "\n")

    print(f"✅ 已生成 {output_path} ({len(steps)} 步，含 1 次致命漂移)")
    return output_path

if __name__ == "__main__":
    make_trace()
