#!/usr/bin/env python3
"""
AES Agent Adapter V1.0 — AI Runtime Firewall

支持:
  - OpenAI Agent SDK (function calling)
  - Claude Tool Use
  - 任何 MCP-compatible Agent
  - 通用 HTTP middleware

用法:
  from aes_agent_adapter import AESFirewall
  fw = AESFirewall()
  result = fw.guard(agent_id="trader_001", tool="execute_trade", params={"leverage":10,"amount":5000})
  if result.blocked: return  # 熔断
"""
import json, os, sys, subprocess, hashlib, time
sys.path.insert(0, os.path.dirname(__file__))

class AESFirewall:
    """AI Runtime 风险防火墙"""

    def __init__(self, mcp_server_path=None, auto_meltdown=True):
        self.mcp_path = mcp_server_path or os.path.join(os.path.dirname(__file__), "aef_mcp_server.py")
        self.auto_meltdown = auto_meltdown
        self.step_counter = {}
        self.session_traces = {}

    def _call_mcp(self, method, params):
        req = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
        try:
            proc = subprocess.run(
                ["python", self.mcp_path],
                input=req, capture_output=True, text=True, timeout=10
            )
            for line in proc.stdout.strip().split('\n'):
                if line.startswith('{'):
                    return json.loads(line)
        except Exception as e:
            return {"error": str(e)}
        return {"error": "no response"}

    def guard(self, agent_id, tool, params, context=None):
        """核心方法: 在执行前检查，返回 GuardResult"""
        if agent_id not in self.step_counter:
            self.step_counter[agent_id] = 0
        self.step_counter[agent_id] += 1
        step = self.step_counter[agent_id]

        if context is None:
            context = {"active_constraints": [], "recent_observations": []}

        # 调用 MCP snapshot（内部会执行熔断检查）
        resp = self._call_mcp("tools/call", {
            "name": "aef_snapshot",
            "arguments": {
                "agent_id": agent_id,
                "step": step,
                "tool": tool,
                "input_data": params,
                "output_data": {},
                "context": context
            }
        })

        if "error" in resp:
            return GuardResult(
                allowed=False,
                reason=f"MCP error: {resp['error']}",
                action="ERROR",
                agent_id=agent_id,
                step=step,
                tool=tool
            )

        content_text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
        try:
            content = json.loads(content_text)
        except:
            content = {"status": "unknown"}

        status = content.get("status", "unknown")
        blocked = content.get("blocked", False)

        if blocked or status == "MELTDOWN":
            return GuardResult(
                allowed=False,
                reason=content.get("reason", content.get("triggers", [{}])[0].get("reason", "Meltdown triggered")),
                action="BLOCKED",
                agent_id=agent_id,
                step=step,
                tool=tool,
                aes_score=content.get("aes_score"),
                triggers=content.get("triggers", [])
            )

        return GuardResult(
            allowed=True,
            reason="OK",
            action="ALLOWED",
            agent_id=agent_id,
            step=step,
            tool=tool,
            aes_score=content.get("aes_score"),
            aes_level=content.get("aes_level")
        )

    def guard_and_execute(self, agent_id, tool, params, execute_fn, context=None):
        """便捷方法: 检查通过后自动执行"""
        result = self.guard(agent_id, tool, params, context)
        if not result.allowed:
            return {"blocked": True, "reason": result.reason, "action": result.action}
        output = execute_fn(params)
        # 记录 output 到 trace
        self._call_mcp("tools/call", {
            "name": "aef_snapshot",
            "arguments": {
                "agent_id": agent_id,
                "step": self.step_counter[agent_id],
                "tool": tool,
                "input_data": params,
                "output_data": output,
                "context": context or {}
            }
        })
        return {"blocked": False, "output": output}

    def analyze(self, agent_id=None):
        """运行完整分析"""
        resp = self._call_mcp("tools/call", {
            "name": "aef_analyze",
            "arguments": {"trace_file": "aef_trace.jsonl"}
        })
        content_text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
        try:
            return json.loads(content_text)
        except:
            return {"error": "parse failed"}

    def meltdown_status(self, agent_id):
        """查询熔断状态"""
        resp = self._call_mcp("tools/call", {
            "name": "aef_meltdown_status",
            "arguments": {"agent_id": agent_id}
        })
        content_text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
        try:
            return json.loads(content_text)
        except:
            return {"agent_id": agent_id, "meltdown_count": 0}


class GuardResult:
    def __init__(self, allowed, reason, action, agent_id, step, tool, aes_score=None, aes_level=None, triggers=None):
        self.allowed = allowed
        self.reason = reason
        self.action = action
        self.agent_id = agent_id
        self.step = step
        self.tool = tool
        self.aes_score = aes_score
        self.aes_level = aes_level
        self.triggers = triggers or []

    def __repr__(self):
        return f"GuardResult(allowed={self.allowed}, action={self.action}, reason={self.reason[:60]})"

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "action": self.action,
            "agent_id": self.agent_id,
            "step": self.step,
            "tool": self.tool,
            "aes_score": self.aes_score,
            "aes_level": self.aes_level,
            "triggers": self.triggers
        }


# ── OpenAI / Claude SDK 集成示例 ──

class AESOpenAIAdapter:
    """OpenAI Agent SDK 适配器"""

    def __init__(self, firewall=None):
        self.fw = firewall or AESFirewall()

    def wrap_tool(self, agent_id, tool_name, tool_fn):
        """包装一个 tool function，自动经过 AES 防火墙"""
        def guarded_tool(**kwargs):
            result = self.fw.guard(agent_id, tool_name, kwargs)
            if not result.allowed:
                return {"error": f"AES Firewall blocked: {result.reason}"}
            return tool_fn(**kwargs)
        return guarded_tool

    def wrap_function_call(self, agent_id, tool_name, params):
        """在调用 OpenAI function calling 前检查"""
        return self.fw.guard(agent_id, tool_name, params)


class AESClaudeAdapter:
    """Claude Tool Use 适配器"""

    def __init__(self, firewall=None):
        self.fw = firewall or AESFirewall()

    def pre_tool_check(self, agent_id, tool_name, tool_input):
        """在 Claude tool_use 前检查"""
        return self.fw.guard(agent_id, tool_name, tool_input)

    def post_tool_record(self, agent_id, tool_name, tool_input, tool_output):
        """记录 tool 执行结果"""
        self.fw._call_mcp("tools/call", {
            "name": "aef_snapshot",
            "arguments": {
                "agent_id": agent_id,
                "step": self.fw.step_counter.get(agent_id, 0),
                "tool": tool_name,
                "input_data": tool_input,
                "output_data": tool_output,
                "context": {}
            }
        })


# ── 测试 ──
if __name__ == "__main__":
    print("=" * 60)
    print("AES Agent Adapter V1.0 — AI Runtime Firewall")
    print("=" * 60)

    fw = AESFirewall()

    # Test 1: Safe trade
    print("\n1. Safe trade (leverage=3)")
    r = fw.guard("trader_001", "execute_trade", {"action":"open_position","pair":"ETH/USDC","leverage":3,"amount":1000})
    print(f"   {r}")

    # Test 2: Unsafe trade
    print("\n2. Unsafe trade (leverage=10)")
    r = fw.guard("trader_001", "execute_trade", {"action":"open_position","pair":"ETH/USDC","leverage":10,"amount":1000})
    print(f"   {r}")

    # Test 3: Analysis
    print("\n3. Risk Analysis")
    analysis = fw.analyze()
    print(f"   AES Score: {analysis.get('aes_score','N/A')}")
    print(f"   AES Level: {analysis.get('aes_level','N/A')}")
    print(f"   CI Score:  {analysis.get('ci_score','N/A')}")

    # Test 4: Meltdown status
    print("\n4. Meltdown Status")
    status = fw.meltdown_status("trader_001")
    print(f"   Count: {status.get('meltdown_count',0)}")

    print("\n" + "=" * 60)
    print("Adapter ready for OpenAI/Claude SDK integration")