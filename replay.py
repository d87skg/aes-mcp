#!/usr/bin/env python3
"""
AES Canonical Replay Suite v0.1
保证: 相同 trace + 相同 spec version → 确定性输出 + 确定性 hash
"""
import json, hashlib, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from oracle_adapter import generate_attestation

MANIFEST = "golden_traces/manifest.json"
REPLAY_LOG = "golden_traces/replay_log.json"

def replay_all():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    results = {}
    for trace in manifest["traces"]:
        tid = trace["trace_id"]
        trace_path = os.path.join("golden_traces", trace["filename"])
        att = generate_attestation(trace_path)
        del att["attestation"]["_private_key"]
        payload = json.dumps(att, sort_keys=True, ensure_ascii=False)
        det_hash = hashlib.sha256(payload.encode()).hexdigest()
        results[tid] = {
            "trace_id": tid,
            "aes_score": att["aes_score"],
            "risk_vector_hash": att["attestation"]["risk_vector_hash"],
            "deterministic_hash": det_hash,
            "death_mode": att["metadata"]["death_mode_archetype"],
            "adj_er": att["adj_er"]
        }

    replay_record = {
        "replay_version": "1.0",
        "spec_versions": {
            "aes_score": "v0.1.1",
            "risk_vector": "v0.1",
            "oracle": "v0.1"
        },
        "results": results,
        "all_hashes": {tid: r["deterministic_hash"] for tid, r in results.items()}
    }

    with open(REPLAY_LOG, "w", encoding="utf-8") as f:
        json.dump(replay_record, f, ensure_ascii=False, indent=2)

    print("AES Canonical Replay Suite v0.1")
    print("=" * 75)
    for tid, r in results.items():
        print(f"  {tid}: AES={r['aes_score']:.0f} | Death={r['death_mode']:25s} | Hash={r['deterministic_hash'][:16]}...")
    print("=" * 75)
    print(f"Replay log: {REPLAY_LOG}")
    return replay_record

if __name__ == "__main__":
    replay_all()