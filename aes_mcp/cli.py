"""AES-MCP CLI — Runtime Security for AI Agents"""
import argparse, json, sys, os

def main():
    parser = argparse.ArgumentParser(description="AES-MCP Runtime Security")
    parser.add_argument("--config", default=None, help="Policy config file")
    parser.add_argument("--demo", choices=["episode_1","episode_2"], help="Run demo")
    parser.add_argument("--port", type=int, default=8080, help="MCP port")
    args = parser.parse_args()

    if args.demo:
        cli_dir = os.path.dirname(os.path.abspath(__file__))
        demos_dir = os.path.join(cli_dir, "..", "demos")
        demo_map = {"episode_1": "episode_1_meltdown.json", "episode_2": "episode_2_deletion.json"}
        demo_path = os.path.normpath(os.path.join(demos_dir, demo_map[args.demo]))
        if os.path.exists(demo_path):
            with open(demo_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        print(line.strip())
            print(f"\nDemo: {args.demo} — replay with: aes-mcp --replay {demo_path}")
        else:
            print(f"Demo file not found: {demo_path}")
        return

    print("AES-MCP v2.0.0 — AI Runtime Security")
    print("Starting MCP server...")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from aes_mcp.server import AESMCPServer
    AESMCPServer().run()

if __name__ == "__main__":
    main()