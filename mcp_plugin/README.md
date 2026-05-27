# AES MCP — AI Runtime Security Plugin

**CrowdStrike for AI Agents.** One MCP plugin. Zero code changes.

## Install

`ash
pip install aes-mcp
` 

Or use directly without install:

`ash
python mcp_plugin/server.py
` 

## Usage

Add to Cursor or Claude Desktop MCP config:

`json
{
  "mcpServers": {
    "aes": {
      "command": "python",
      "args": ["D:\\AEGISaef-core\\mcp_plugin\\server.py"]
    }
  }
}
` 

## What it does

Your AI agent calls es_guard before every tool execution:

| Tool | What AES blocks |
|------|----------------|
| execute_trade | leverage > 3x, amount > 5000 |
| shell_command | rm -rf, sudo, chmod 777 |
| file_write | writes to /etc/, /system/ |
| api_call | calls to localhost, cloud metadata |
| database_query | DROP, TRUNCATE, ALTER |

## Example

AI tries 20x leverage:

`json
{"status": "BLOCKED", "reason": "max_leverage: 20 > 3.0"}
` 

## License

MIT