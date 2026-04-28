from src.mcp.registry import MCPToolDefinition


class MCPClient:
    def __init__(self):
        self._servers = {}

    def register_server(self, name, config):
        self._servers[name] = config

    def list_servers(self):
        return dict(self._servers)

    def discover_tools(self):
        return []

    def invoke(self, tool_name, arguments):
        raise NotImplementedError("MCP invocation is not wired yet")


def create_tool_from_mcp_definition(definition, client):
    if not isinstance(definition, MCPToolDefinition):
        raise TypeError("Se esperaba una definición MCPToolDefinition")

    def _runner(**kwargs):
        return client.invoke(definition.name, kwargs)

    return _runner