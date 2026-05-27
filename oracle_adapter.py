#!/usr/bin/env python3
"""
AER Oracle Adapter v0.1 — Phase 1: Attestation Payload + Sign + Verify
"""
import json, os, sys, hashlib, time, secrets
sys.path.insert(0, os.path.dirname(__file__))
from risk_vector import compute_risk_vector

def generate_keypair():
    sk = secrets.token_hex(32)
    pk = hashlib.sha256(sk.encode()).hexdigest()[:40]
    return sk, pk

def sign(payload_bytes, sk):
    return hashlib.sha256(payload_bytes + sk.encode()).hexdigest()

def verify(payload_bytes, sig, pk, sk):
    expected = hashlib.sha256(payload_bytes + sk.encode()).hexdigest()
    return sig == expected

def merkle_root(steps):
    hashes = [hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest() for s in steps]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1: hashes.append(hashes[-1])
        hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest() for i in range(0, len(hashes), 2)]
    return hashes[0] if hashes else "0x0"

def generate_attestation(trace_path, signer_name="oracle_node_01"):
    rv = compute_risk_vector(trace_path)
    steps = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): steps.append(json.loads(line))
    trace_root = merkle_root(steps)
    now = int(time.time())
    risk_vector_canonical = {
        "stability": {"score": rv["aes_score"], "level": rv["stability"]},
        "contagion": {"cpf_raw": rv["shadow_metrics"]["cpf_raw"], "cpf_scaled": rv["shadow_metrics"]["cpf_scaled"], "band": rv["contagion"]},
        "decay": {"led_score": rv["shadow_metrics"]["led_score"], "level": rv["decay"]},
        "containment": {"score": rv["containment"], "blast_radius": rv["shadow_metrics"]["blast_radius"]}
    }
    sk, pk = generate_keypair()
    rv_json = json.dumps(risk_vector_canonical, sort_keys=True, ensure_ascii=False)
    rv_hash = hashlib.sha256(rv_json.encode()).hexdigest()
    sig_payload = f"{rv['trace_id']}:{now}:{rv_hash}:{trace_root}"
    signature = sign(sig_payload.encode(), sk)
    attestation = {
        "trace_id": rv["trace_id"], "agent_id": steps[0].get("agent_id", "unknown"),
        "timestamp": now, "aes_score": rv["aes_score"], "aes_level": rv["aes_level"],
        "risk_vector": risk_vector_canonical, "adj_er": rv["er_layer"]["adjusted_er_penalty"],
        "er_detail": {
            "explicit_loss": rv["er_layer"]["explicit_loss"],
            "implicit_loss": rv["er_layer"]["implicit_loss"],
            "effective_loss": rv["er_layer"]["effective_loss"],
            "cpf_multiplier": rv["er_layer"]["cpf_multiplier"],
            "led_multiplier": rv["er_layer"]["led_multiplier"],
            "containment_effective": rv["er_layer"]["containment_effective"],
            "formula": rv["er_layer"]["formula"]
        },
        "attestation": {
            "oracle_version": "AER-v0.1", "risk_vector_hash": rv_hash,
            "trace_root": trace_root, "timestamp": now,
            "signer": signer_name, "public_key": pk, "signature": signature,
            "_private_key": sk
        },
        "metadata": {
            "spec_version": "AES_RISK_VECTOR_SPEC_v0.1",
            "engine_versions": {"aes_scorer": "v0.1.1", "drift_engine": "v2.1", "cpf_engine": "v0.2-alpha", "ese_engine": "v0.1", "containment_engine": "v0.2"},
            "death_mode_archetype": classify_death_mode(rv)
        }
    }
    return attestation

def classify_death_mode(rv):
    c, d = rv["contagion"], rv["decay"]
    if c == "SYSTEMIC": return "systemic_collapse"
    if d == "HIGH": return "chronic_decay"
    if c == "PRECURSOR": return "coordination_instability"
    if rv["er_layer"]["explicit_loss"] > 0: return "isolated_acute"
    return "healthy"

def verify_attestation(att):
    a = att["attestation"]
    rv = att["risk_vector"]
    rv_json = json.dumps(rv, sort_keys=True, ensure_ascii=False)
    rv_hash = hashlib.sha256(rv_json.encode()).hexdigest()
    if rv_hash != a["risk_vector_hash"]: return False, "Hash mismatch"
    sig_payload = f"{att['trace_id']}:{a['timestamp']}:{rv_hash}:{a['trace_root']}"
    sk = a.get("_private_key", "")
    if not verify(sig_payload.encode(), a["signature"], a["public_key"], sk): return False, "Sig fail"
    return True, "Valid"

def run_all():
    manifest_path = "golden_traces/manifest.json"
    if not os.path.exists(manifest_path): print("ERROR"); return
    with open(manifest_path, "r", encoding="utf-8") as f: manifest = json.load(f)
    print("\n" + "=" * 90)
    print("AER Oracle Adapter v0.1 — Attestation Generation + Verification")
    print("=" * 90)
    attestations, all_ok = [], True
    for trace in manifest["traces"]:
        tid = trace["trace_id"]
        att = generate_attestation(os.path.join("golden_traces", trace["filename"]))
        valid, msg = verify_attestation(att)
        if not valid: all_ok = False
        print(f"  {tid}: {'OK' if valid else 'FAIL'} | DeathMode={att['metadata']['death_mode_archetype']} | AdjER={att['adj_er']} | Hash={att['attestation']['risk_vector_hash'][:12]}...")
        # 移除私钥再保存
        del att["attestation"]["_private_key"]
        attestations.append(att)
    print("-" * 90)
    print(f"  All valid: {all_ok}")
    print("=" * 90)
    output = {"oracle_version": "AER-v0.1", "generated_at": int(time.time()), "total": len(attestations), "all_valid": all_ok, "attestations": attestations}
    with open("golden_traces/oracle_attestations.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Saved: golden_traces/oracle_attestations.json")

if __name__ == "__main__":
    run_all()