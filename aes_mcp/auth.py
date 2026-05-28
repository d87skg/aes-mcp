"""AES Authentication Module — HMAC-based admin verification"""
import os, hmac, hashlib, sys

def _get_required_env(key):
    val = os.environ.get(key)
    if not val:
        print(f"AES-MCP: FATAL - Environment variable {key} must be set", file=sys.stderr)
        print(f"  Example: set {key}=your-secret-value", file=sys.stderr)
        sys.exit(1)
    return val

def get_signing_key():
    return _get_required_env("AES_SIGNING_KEY").encode()

def verify_admin(token):
    if not token:
        return False
    expected = _get_required_env("AES_ADMIN_TOKEN")
    return hmac.compare_digest(token, expected)

def sign_proof(proof_id, agent_id, params_hash, result_hash):
    payload = f"{proof_id}:{agent_id}:{params_hash}:{result_hash}"
    return hmac.new(get_signing_key(), payload.encode(), "sha256").hexdigest()

def verify_proof_signature(proof_id, agent_id, params_hash, result_hash, signature):
    expected = sign_proof(proof_id, agent_id, params_hash, result_hash)
    return hmac.compare_digest(expected, signature)