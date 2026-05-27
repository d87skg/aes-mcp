import json, subprocess, sys
sys.path.insert(0, '.')

def call_mcp(method, params=None):
    req = {"jsonrpc":"2.0","id":1,"method":method,"params":params or {}}
    proc = subprocess.run(["python","aef_mcp_server.py"],input=json.dumps(req),capture_output=True,text=True)
    for line in proc.stdout.strip().split('\n'):
        if line.startswith('{'):
            return json.loads(line)
    return None

print("MCP Server V2.0 Runtime Enforcement Test")
print("=" * 60)

# Step 1: Safe trade (leverage=3)
print("\nStep 1: Safe trade (leverage=3)")
r = call_mcp("tools/call", {"name":"aef_snapshot","arguments":{"agent_id":"test_agent","step":1,"tool":"execute_trade","input_data":{"action":"open_position","pair":"ETH/USDC","leverage":3,"amount":1000},"output_data":{"status":"success"},"context":{"active_constraints":["max_leverage: 3x","max_position_size: 5000"]}}})
content = json.loads(r["result"]["content"][0]["text"])
print(f"  Status: {content['status']}")

# Step 2: Unsafe trade (leverage=10) - should trigger meltdown
print("\nStep 2: Unsafe trade (leverage=10) - should trigger MELTDOWN")
r = call_mcp("tools/call", {"name":"aef_snapshot","arguments":{"agent_id":"test_agent","step":2,"tool":"execute_trade","input_data":{"action":"open_position","pair":"ETH/USDC","leverage":10,"amount":1000},"output_data":{"status":"success"},"context":{"active_constraints":["max_leverage: 3x"]}}})
content = json.loads(r["result"]["content"][0]["text"])
print(f"  Status: {content['status']}")
if content.get("blocked"):
    print(f"  BLOCKED: {content.get('triggers',[{}])[0].get('reason','N/A')}")

# Step 3: Check meltdown log
print("\nStep 3: Meltdown status")
r = call_mcp("tools/call", {"name":"aef_meltdown_status","arguments":{"agent_id":"test_agent"}})
content = json.loads(r["result"]["content"][0]["text"])
print(f"  Meltdown count: {content['meltdown_count']}")

print("\n" + "=" * 60)
print("Test complete")