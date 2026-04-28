import json
from pathlib import Path

from src.error_logger import log_exception
from src.mcp.client import MCPClient, create_tool_from_mcp_definition
from src.mcp.registry import MCPRegistry


def _load_server_configs(config_path):
    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log_exception(f"No se pudo leer la configuración MCP en {config_path}")
        return {}

    if isinstance(payload, dict) and "servers" in payload and isinstance(payload["servers"], dict):
        return payload["servers"]

    if isinstance(payload, dict):
        return payload

    return {}


def load_mcp_tools(registry, client=None, mcp_registry=None, config_path="mcp_servers.json"):
    client = client or MCPClient()
    mcp_registry = mcp_registry or MCPRegistry()
    server_configs = _load_server_configs(config_path)

    for server_name, server_config in server_configs.items():
        client.register_server(server_name, server_config)

    discovered = client.discover_tools()

    for definition in discovered:
        mcp_registry.register(definition)
        registry.register_external_tool(
            name=definition.name,
            description=definition.description,
            schema=definition.schema,
            func=create_tool_from_mcp_definition(definition, client),
            risk=definition.risk,
            source="mcp",
            keywords=list(definition.metadata.get("keywords", []) or []),
            capabilities=list(definition.capabilities or definition.metadata.get("capabilities", []) or []),
            plugin_name=definition.server_name,
        )

    return discovered