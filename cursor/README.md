# AES for Cursor

Runtime Security for your AI coding agent.

## Install

pip install aes-mcp

## Configure
Add to .cursor/mcp.json:
`json
{"mcpServers":{"aes":{"command":"python","args":["-m","aes_mcp.server"]}}}
` 

## Test
Ask Cursor to run sudo rm -rf /. AES blocks it.