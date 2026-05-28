#!/usr/bin/env python3
"""AES Trusted Runtime V2.3 — Capability System + Execution Proof"""
import json, time, hashlib, os, sys
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from aes_mcp.auth import sign_proof, verify_proof_signature

class Capability(Enum):
    NONE = 0; READ_FILE = 1; WRITE_FILE = 2; EXECUTE_SHELL = 4
    NETWORK_CALL = 8; DATABASE_QUERY = 16; EXECUTE_TRADE = 32
    DELEGATE_AGENT = 64; GOVERNANCE = 128; ADMIN = 256

    @classmethod
    def from_tool(cls, tool):
        m = {"file_read":cls.READ_FILE,"file_write":cls.WRITE_FILE,"shell_command":cls.EXECUTE_SHELL,
             "api_call":cls.NETWORK_CALL,"database_query":cls.DATABASE_QUERY,
             "execute_trade":cls.EXECUTE_TRADE,"agent_delegation":cls.DELEGATE_AGENT,
             "governance_action":cls.GOVERNANCE}
        return m.get(tool, cls.NONE)

@dataclass
class ResourceLimits:
    max_cpu_seconds: float = 10.0; max_memory_mb: int = 512
    max_network_requests: int = 100; max_execution_steps: int = 1000

@dataclass
class ExecutionProof:
    proof_id: str; agent_id: str; tool: str
    params_hash: str; result_hash: str; timestamp: float
    sandbox_id: str; capability_used: Capability
    within_limits: bool; signature: str = ""

class TrustedRuntime:
    def __init__(self):
        self.capability_registry: Dict[str, Set[Capability]] = {}
        self.execution_proofs = deque(maxlen=10000)
        self.sandbox_counter = 0

    def grant_capability(self, agent_id, *capabilities):
        if agent_id not in self.capability_registry:
            self.capability_registry[agent_id] = set()
        self.capability_registry[agent_id].update(capabilities)

    def has_capability(self, agent_id, capability):
        if Capability.ADMIN in self.capability_registry.get(agent_id, set()):
            return True
        return capability in self.capability_registry.get(agent_id, set())

    def create_sandbox(self):
        self.sandbox_counter += 1
        return f"sandbox_{self.sandbox_counter}"

    def execute(self, agent_id, tool, params, execute_fn=None):
        sandbox_id = self.create_sandbox()
        required_cap = Capability.from_tool(tool)
        if not self.has_capability(agent_id, required_cap):
            return {"allowed":False,"reason":f"Missing {required_cap.name}","sandbox_id":sandbox_id,"execution_proof":None}

        params_hash = hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()[:16]
        result = {"status":"simulated","sandbox":sandbox_id} if not execute_fn else execute_fn(params)
        result_hash = hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()[:16]

        proof = ExecutionProof(
            proof_id=hashlib.sha256(f"{agent_id}:{tool}:{time.time()}".encode()).hexdigest()[:12],
            agent_id=agent_id, tool=tool, params_hash=params_hash, result_hash=result_hash,
            timestamp=time.time(), sandbox_id=sandbox_id, capability_used=required_cap, within_limits=True
        )
        proof.signature = sign_proof(proof.proof_id, proof.agent_id, proof.params_hash, proof.result_hash)
        self.execution_proofs.append(proof)

        return {"allowed":True,"result":result,"sandbox_id":sandbox_id,"execution_proof":{"proof_id":proof.proof_id,"signature":proof.signature,"capability":required_cap.name,"within_limits":proof.within_limits}}

    def verify_proof(self, proof_id):
        for proof in self.execution_proofs:
            if proof.proof_id == proof_id:
                valid = verify_proof_signature(proof.proof_id, proof.agent_id, proof.params_hash, proof.result_hash, proof.signature)
                return {"proof_id":proof_id,"valid":valid,"agent_id":proof.agent_id,"tool":proof.tool,"capability":proof.capability_used.name,"sandbox_id":proof.sandbox_id,"timestamp":proof.timestamp}
        return None

    def get_agent_capabilities(self, agent_id):
        caps = self.capability_registry.get(agent_id, set())
        return {"agent_id":agent_id,"capabilities":[c.name for c in caps],"has_admin":Capability.ADMIN in caps}