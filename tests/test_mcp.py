import json
import sys
import tempfile
import textwrap
from pathlib import Path
import unittest

from src.core.tool_registry import ToolRegistry
from src.mcp.client import MCPClient
from src.mcp.loader import load_mcp_tools


class MCPIntegrationTests(unittest.TestCase):
    def test_mcp_loader_registers_and_invokes_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            server_script = temp_path / "fake_mcp_server.py"
            config_file = temp_path / "mcp_servers.json"

            server_script.write_text(
                textwrap.dedent(
                    """
                    import json
                    import sys

                    TOOLS = [{
                        "name": "say_hello",
                        "description": "Saluda",
                        "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
                        "capabilities": ["greeting"],
                        "risk": "safe"
                    }]

                    for line in sys.stdin:
                        request = json.loads(line)
                        method = request.get("method")
                        request_id = request.get("id")

                        if method == "initialize":
                            result = {"protocolVersion": "2024-11-05"}
                        elif method == "tools/list":
                            result = {"tools": TOOLS}
                        elif method == "tools/call":
                            arguments = request.get("params", {}).get("arguments", {})
                            result = {"content": [{"type": "text", "text": f"hello {arguments.get('name', 'world')}"}]}
                        else:
                            result = {}

                        print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}), flush=True)
                    """
                ),
                encoding="utf-8",
            )

            config_file.write_text(
                json.dumps(
                    {
                        "servers": {
                            "demo": {
                                "command": [sys.executable],
                                "args": [str(server_script)],
                            }
                        }
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            registry = ToolRegistry()
            client = MCPClient()
            self.addCleanup(client.close)
            discovered = load_mcp_tools(registry, client=client, config_path=str(config_file))

            self.assertEqual(len(discovered), 1)
            self.assertIsNotNone(registry.get("say_hello"))
            self.assertEqual(registry.execute("say_hello", name="Yiujarvis"), "hello Yiujarvis")


if __name__ == "__main__":
    unittest.main()