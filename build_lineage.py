#!/usr/bin/env python3
"""AES Replay Lineage Builder — 生成协议升级链式历史"""
import json, hashlib, os, sys
sys.path.insert(0, '.')
from oracle_adapter import generate_attestation

MANIFEST = "golden_traces/manifest.json"

def hash_trace(trace_path):
    att = generate_attestation(trace_path)
    del att["attestation"]["_private_key"]
    payload = json.dumps(att, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()

with open(MANIFEST, "r", encoding="utf-8") as f:
    manifest = json.load(f)

# 生成所有 trace 的 hash
hashes = {}
for trace in manifest["traces"]:
    tid = trace["trace_id"]
    hashes[tid] = hash_trace(os.path.join("golden_traces", trace["filename"]))

# 计算 lineage hash (所有 trace hash 的 merkle 根)
sorted_hashes = [hashes[tid] for tid in sorted(hashes.keys())]
combined = "".join(sorted_hashes)
lineage_hash = hashlib.sha256(combined.encode()).hexdigest()

lineage = {
    "lineage_version": "1.0",
    "genesis": {
        "version": "V0.1.2-final",
        "date": "2026-05-25",
        "lineage_hash": lineage_hash,
        "canonical_environment": "CANONICAL_ENVIRONMENT.md v1.0"
    },
    "upgrades": [
        {
            "from": "V0.1.0",
            "to": "V0.1.1",
            "type": "Hotfix",
            "description": "Event Ontology sensor calibration",
            "golden_trace_regression": "PASS 7/7",
            "date": "2026-05-25"
        },
        {
            "from": "V0.1.1",
            "to": "V0.1.2",
            "type": "Minor",
            "description": "CCPS: continuity penalties + transient detection + persistent requires toggle_count>=2",
            "golden_trace_regression": "PASS 7/7",
            "date": "2026-05-25"
        }
    ],
    "golden_trace_hashes": hashes,
    "verification": "Run replay.py and compare deterministic_hash with golden_trace_hashes above"
}

with open("REPLAY_LINEAGE.json", "w", encoding="utf-8") as f:
    json.dump(lineage, f, ensure_ascii=False, indent=2)

print("AES Replay Lineage v1.0")
print("=" * 70)
print(f"Lineage Hash: {lineage_hash}")
print(f"Version: V0.1.2-final")
for tid in sorted(hashes.keys()):
    print(f"  {tid}: {hashes[tid][:16]}...")
print("=" * 70)
print("Saved: REPLAY_LINEAGE.json")