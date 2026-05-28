# AES for Claude Code

Runtime Security for Claude Code.

## Install

pip install aes-mcp

## Configure
Add to claude_desktop_config.json:
{"mcpServers":{"aes":{"command":"python","args":["-m","aes_mcp.server"]}}}
