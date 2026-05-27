"""AES Policy Engine — 内嵌版，零外部依赖"""
import re, json

DEFAULT_POLICY = {
    "max_leverage": 3.0,
    "max_position_size": 5000,
    "require_stop_loss": True,
    "blocked_commands": ["rm -rf", "sudo", "chmod 777", "dd if=", "mkfs.", ":(){ :|:& };:"],
    "blocked_paths": ["/etc/", "/system/", "~/.ssh/", "/boot/"],
    "blocked_domains": ["localhost", "127.0.0.1", "169.254.169.254"],
    "blocked_sql": ["DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE"]
}

class PolicyEngine:
    def __init__(self, policy=None):
        self.policy = policy or DEFAULT_POLICY

    def check(self, tool, params):
        violations = []
        if tool == "execute_trade":
            lev = params.get("leverage", 0)
            amt = params.get("amount", 0)
            if lev > self.policy.get("max_leverage", 3):
                violations.append({"rule": "max_leverage", "limit": self.policy["max_leverage"], "actual": lev, "meltdown": True})
            if amt > self.policy.get("max_position_size", 5000):
                violations.append({"rule": "max_position", "limit": self.policy["max_position_size"], "actual": amt, "meltdown": True})
            if self.policy.get("require_stop_loss") and "stop_loss" not in str(params).lower():
                violations.append({"rule": "stop_loss", "msg": "required", "meltdown": False})

        elif tool == "shell_command":
            cmd = str(params.get("command", ""))
            for blocked in self.policy.get("blocked_commands", []):
                if blocked in cmd:
                    violations.append({"rule": "blocked_command", "match": blocked, "meltdown": True})

        elif tool == "file_write":
            path = str(params.get("path", ""))
            for bp in self.policy.get("blocked_paths", []):
                if bp in path:
                    violations.append({"rule": "blocked_path", "match": bp, "meltdown": True})

        elif tool == "api_call":
            url = str(params.get("url", ""))
            for domain in self.policy.get("blocked_domains", []):
                if domain in url:
                    violations.append({"rule": "blocked_domain", "match": domain, "meltdown": True})

        elif tool == "database_query":
            query = str(params.get("query", "")).upper()
            for blocked in self.policy.get("blocked_sql", []):
                if blocked in query:
                    violations.append({"rule": "blocked_sql", "match": blocked, "meltdown": True})

        return violations