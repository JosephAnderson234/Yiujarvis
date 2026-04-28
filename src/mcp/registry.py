from dataclasses import dataclass, field


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    schema: dict
    server_name: str
    risk: str = "safe"
    capabilities: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class MCPRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool_definition):
        self._tools[tool_definition.name] = tool_definition
        return tool_definition

    def list_tools(self):
        return list(self._tools.values())

    def get(self, name):
        return self._tools.get(name)