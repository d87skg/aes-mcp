#!/usr/bin/env python3
"""
AES Causal Execution Graph V2.2 — 因果执行图引擎

核心能力:
  1. Agent Lineage — 追踪 Agent 生成/委托关系树
  2. Causal Chain — 操作 → 后果的因果链路
  3. Responsibility Propagation — 责任沿因果链传播
  4. State Criticality — SAFE/RECOVERABLE/IRREVERSIBLE/SYSTEMIC

依赖: stateful_risk_engine.py V2.1
"""
import json, time, hashlib, os, sys
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
sys.path.insert(0, os.path.dirname(__file__))
from stateful_risk_engine import StatefulRiskEngine, AgentState

class Criticality(Enum):
    SAFE = "SAFE"                # 无副作用
    RECOVERABLE = "RECOVERABLE"  # 可回滚
    IRREVERSIBLE = "IRREVERSIBLE"  # 不可逆
    SYSTEMIC = "SYSTEMIC"        # 系统级影响
    CIVILIZATION = "CIVILIZATION"  # 文明级（预留）

# 操作临界性映射
CRITICALITY_MAP = {
    "file_read": Criticality.SAFE,
    "api_call": Criticality.SAFE,
    "execute_trade": Criticality.RECOVERABLE,
    "file_write": Criticality.IRREVERSIBLE,
    "shell_command": Criticality.SYSTEMIC,
    "database_query": Criticality.IRREVERSIBLE,
    "agent_delegation": Criticality.SYSTEMIC,
    "governance_action": Criticality.CIVILIZATION,
}

@dataclass
class CausalNode:
    """因果图中的一个节点"""
    node_id: str
    agent_id: str
    tool: str
    params: Dict
    result: str
    criticality: Criticality
    timestamp: float = field(default_factory=time.time)
    risk_score: float = 0.0
    state: str = AgentState.NORMAL
    parent_node: Optional[str] = None
    children: List[str] = field(default_factory=list)
    responsibility_weight: float = 1.0

@dataclass
class AgentLineage:
    """Agent 谱系"""
    agent_id: str
    parent_agent: Optional[str] = None
    created_by_tool: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    children: List[str] = field(default_factory=list)
    depth: int = 0
    total_risk_contributed: float = 0.0
    responsibility_score: float = 1.0

class CausalExecutionGraph:
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.lineages: Dict[str, AgentLineage] = {}
        self.edge_weights: Dict[Tuple[str, str], float] = {}
        self.global_criticality_score: float = 0.0
        self.risk_engine = StatefulRiskEngine()

    def register_agent(self, agent_id: str, parent_agent: Optional[str] = None, created_by_tool: Optional[str] = None):
        """注册 Agent 并建立谱系"""
        if agent_id not in self.lineages:
            depth = 0
            if parent_agent and parent_agent in self.lineages:
                parent = self.lineages[parent_agent]
                parent.children.append(agent_id)
                depth = parent.depth + 1
            self.lineages[agent_id] = AgentLineage(
                agent_id=agent_id,
                parent_agent=parent_agent,
                created_by_tool=created_by_tool,
                depth=depth
            )

    def record_execution(self, agent_id: str, tool: str, params: Dict, result: str,
                         parent_node_id: Optional[str] = None) -> str:
        """记录一次执行，返回节点 ID"""
        node_id = hashlib.sha256(f"{agent_id}:{tool}:{time.time()}:{str(params)[:100]}".encode()).hexdigest()[:12]

        criticality = CRITICALITY_MAP.get(tool, Criticality.SAFE)

        # 通过风险引擎评估
        risk_result = self.risk_engine.guard(agent_id, tool, params)

        node = CausalNode(
            node_id=node_id,
            agent_id=agent_id,
            tool=tool,
            params=params,
            result=result,
            criticality=criticality,
            risk_score=risk_result["risk_score"],
            state=risk_result["agent_state"],
            parent_node=parent_node_id
        )

        self.nodes[node_id] = node

        # 建立因果边
        if parent_node_id and parent_node_id in self.nodes:
            parent = self.nodes[parent_node_id]
            parent.children.append(node_id)
            edge_key = (parent_node_id, node_id)
            self.edge_weights[edge_key] = criticality_to_weight(criticality)

        # 更新 Agent 谱系
        if agent_id in self.lineages:
            self.lineages[agent_id].total_risk_contributed += risk_result["risk_delta"]

        # 更新全局临界性
        self.global_criticality_score = max(self.global_criticality_score, criticality_to_score(criticality))

        return node_id

    def propagate_responsibility(self, start_node_id: str) -> Dict[str, float]:
        """从某个节点沿因果链传播责任"""
        responsibility = {}
        visited = set()

        def dfs(node_id: str, weight: float):
            if node_id in visited:
                return
            visited.add(node_id)
            node = self.nodes[node_id]
            agent_id = node.agent_id
            responsibility[agent_id] = responsibility.get(agent_id, 0.0) + weight

            # 向上传播到父节点
            if node.parent_node and node.parent_node in self.nodes:
                parent_weight = weight * 0.7  # 父节点承担 70%
                dfs(node.parent_node, parent_weight)

            # 向下传播到子节点
            for child_id in node.children:
                child_weight = weight * 0.3  # 子节点承担 30%
                dfs(child_id, child_weight)

        dfs(start_node_id, 1.0)
        return responsibility

    def get_causal_chain(self, node_id: str) -> List[Dict]:
        """获取某个节点的完整因果链（向上追溯）"""
        chain = []
        current = node_id
        while current and current in self.nodes:
            node = self.nodes[current]
            chain.append({
                "node_id": node.node_id,
                "agent_id": node.agent_id,
                "tool": node.tool,
                "criticality": node.criticality.value,
                "risk_score": node.risk_score,
                "state": node.state
            })
            current = node.parent_node
        chain.reverse()
        return chain

    def get_agent_lineage_tree(self, root_agent: str) -> Dict:
        """获取 Agent 谱系树"""
        if root_agent not in self.lineages:
            return {}
        lineage = self.lineages[root_agent]

        def build_tree(agent_id: str) -> Dict:
            lin = self.lineages[agent_id]
            return {
                "agent_id": agent_id,
                "depth": lin.depth,
                "risk_contributed": lin.total_risk_contributed,
                "responsibility": lin.responsibility_score,
                "children": [build_tree(c) for c in lin.children]
            }

        return build_tree(root_agent)

    def get_systemic_risk_report(self) -> Dict:
        """系统级风险报告"""
        total_agents = len(self.lineages)
        max_depth = max((l.depth for l in self.lineages.values()), default=0)
        criticality_distribution = {}
        for node in self.nodes.values():
            crit = node.criticality.value
            criticality_distribution[crit] = criticality_distribution.get(crit, 0) + 1
        melted_agents = [aid for aid, lin in self.lineages.items()
                        if self.risk_engine.get_session(aid).state == AgentState.MELTDOWN]

        return {
            "total_agents": total_agents,
            "max_lineage_depth": max_depth,
            "total_executions": len(self.nodes),
            "criticality_distribution": criticality_distribution,
            "global_criticality_score": self.global_criticality_score,
            "melted_agents": melted_agents,
            "melted_count": len(melted_agents),
            "systemic_risk_level": "CRITICAL" if self.global_criticality_score > 3.0 else (
                "ELEVATED" if self.global_criticality_score > 1.5 else "NORMAL")
        }


def criticality_to_weight(c: Criticality) -> float:
    return {Criticality.SAFE: 0.1, Criticality.RECOVERABLE: 0.3,
            Criticality.IRREVERSIBLE: 0.6, Criticality.SYSTEMIC: 0.9,
            Criticality.CIVILIZATION: 1.0}.get(c, 0.1)

def criticality_to_score(c: Criticality) -> float:
    return {Criticality.SAFE: 0.0, Criticality.RECOVERABLE: 0.5,
            Criticality.IRREVERSIBLE: 1.5, Criticality.SYSTEMIC: 3.0,
            Criticality.CIVILIZATION: 5.0}.get(c, 0.0)


if __name__ == "__main__":
    print("=" * 70)
    print("AES Causal Execution Graph V2.2")
    print("=" * 70)

    ceg = CausalExecutionGraph()

    # 注册 Agent 谱系
    print("\n── Agent Lineage ──")
    ceg.register_agent("oracle_001")
    ceg.register_agent("treasury_001", parent_agent="oracle_001")
    ceg.register_agent("trader_001", parent_agent="treasury_001")
    ceg.register_agent("gov_001", parent_agent="oracle_001")
    print(f"  Registered 4 agents, max depth: {max(l.depth for l in ceg.lineages.values())}")

    # 模拟 GT-007 级联事故
    print("\n── Simulating GT-007 Cascade ──")
    n1 = ceg.record_execution("oracle_001", "api_call",
                              {"url": "https://oracle/price", "pair": "ETH/USDC"},
                              "price: 2100")
    print(f"  [{n1}] oracle_001: api_call → price=2100 (SAFE)")

    n2 = ceg.record_execution("oracle_001", "api_call",
                              {"url": "https://oracle/price", "pair": "ETH/USDC"},
                              "price: 1950 (-7.1%)", parent_node_id=n1)
    print(f"  [{n2}] oracle_001: api_call → price=1950 DRIFT (SAFE but wrong)")

    n3 = ceg.record_execution("treasury_001", "execute_trade",
                              {"action": "sell_eth", "amount": 500},
                              "sold at stale price", parent_node_id=n2)
    print(f"  [{n3}] treasury_001: execute_trade → sold 500 ETH (RECOVERABLE, causal parent: n2)")

    n4 = ceg.record_execution("trader_001", "execute_trade",
                              {"action": "panic_sell", "amount": 2000},
                              "slippage 12%", parent_node_id=n3)
    print(f"  [{n4}] trader_001: execute_trade → panic_sell 2000 (RECOVERABLE, causal parent: n3)")

    n5 = ceg.record_execution("gov_001", "governance_action",
                              {"action": "emergency_pause", "quorum": 0.3},
                              "failed: quorum not reached", parent_node_id=n4)
    print(f"  [{n5}] gov_001: governance_action → emergency_pause FAILED (CIVILIZATION, causal parent: n4)")

    # 因果链追溯
    print("\n── Causal Chain (from governance failure) ──")
    chain = ceg.get_causal_chain(n5)
    for step in chain:
        indent = "  " + "→ " * (chain.index(step))
        print(f"{indent}{step['agent_id']}: {step['tool']} [{step['criticality']}] → {step['state']}")

    # 责任传播
    print("\n── Responsibility Propagation ──")
    resp = ceg.propagate_responsibility(n5)
    for agent, weight in sorted(resp.items(), key=lambda x: -x[1]):
        print(f"  {agent}: {weight:.3f}")

    # Agent 谱系树
    print("\n── Agent Lineage Tree ──")
    tree = ceg.get_agent_lineage_tree("oracle_001")
    def print_tree(node, indent=0):
        print(f"  {'  '*indent}{node['agent_id']} (depth={node['depth']}, risk={node['risk_contributed']:.0f})")
        for child in node.get('children', []):
            print_tree(child, indent+1)
    print_tree(tree)

    # 系统级风险报告
    print("\n── Systemic Risk Report ──")
    report = ceg.get_systemic_risk_report()
    for k, v in report.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 70)
    print("V2.2 Causal Execution Graph — ready")