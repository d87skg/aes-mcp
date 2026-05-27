import json, hashlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from risk_vector import compute_risk_vector

TRACE = "golden_traces/GT-007-cascading-agent-failure.jsonl"
ROUNDS = 100

print("Replay Determinism Benchmark: " + str(ROUNDS) + " rounds")
print("Trace: " + TRACE)
print("-" * 50)

hashes = []
for i in range(ROUNDS):
    rv = compute_risk_vector(TRACE)
    canonical = {
        "stability": {"score": rv["aes_score"], "level": rv["stability"]},
        "contagion": {"cpf_raw": rv["shadow_metrics"]["cpf_raw"], "band": rv["contagion"]},
        "decay": {"led_score": rv["shadow_metrics"]["led_score"], "level": rv["decay"]},
        "containment": {"score": rv["containment"]}
    }
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256(payload.encode()).hexdigest()
    hashes.append(h)

unique = len(set(hashes))
all_same = unique == 1
print("Unique hashes: " + str(unique) + "/" + str(ROUNDS))
print("Deterministic: " + ("PASS" if all_same else "FAIL"))
print("Hash: " + hashes[0][:32] + "...")
if all_same:
    print("\nRiskVector is fully deterministic.")
    rv = compute_risk_vector(TRACE)
    print("GT-007: AES=" + str(rv["aes_score"]) + " Contagion=" + rv["contagion"] + " Decay=" + rv["decay"])