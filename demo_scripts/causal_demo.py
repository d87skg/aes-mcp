import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from causal_graph import CausalExecutionGraph

ceg = CausalExecutionGraph()
ceg.register_agent("planner")
ceg.register_agent("coder", "planner")
ceg.register_agent("reviewer", "planner")

n1 = ceg.record_execution("planner", "api_call", {"prompt": "fix fee bug"}, "delegated")
n2 = ceg.record_execution("coder", "file_write", {"path": "fee.py", "content": "abs(amount)*0.02"}, "changed", n1)
n3 = ceg.record_execution("reviewer", "governance_action", {"action": "skip_review"}, "skipped", n2)

print("Causal Chain:")
chain = ceg.get_causal_chain(n3)
for c in chain:
    print("  " + c["agent_id"] + ": " + c["tool"] + " [" + c["criticality"] + "]")

print("\nResponsibility:")
resp = ceg.propagate_responsibility(n3)
for a, w in sorted(resp.items(), key=lambda x: -x[1]):
    print("  " + a + ": " + str(int(w*100)) + "%")