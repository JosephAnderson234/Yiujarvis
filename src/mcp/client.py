import json
import os
import subprocess
import threading
from dataclasses import dataclass, field

from src.error_logger import log_exception
from src.mcp.registry import MCPToolDefinition


@dataclass
class MCPServerConfig:
    command: list[str]
    args: list[str] = field(default_factory=list)
    cwd: str | None = None
    env: dict = field(default_factory=dict)
    transport: str = "stdio"


class _MCPConnection:
    def __init__(self, server_name, config):
        self.server_name = server_name
        self.config = config if isinstance(config, MCPServerConfig) else MCPServerConfig(**config)
        self.process = None
        self._request_id = 0
        self._lock = threading.Lock()

    def start(self):
        if self.process is not None:
            return

        command = [*self.config.command, *self.config.args]
        env = os.environ.copy()
        env.update(self.config.env or {})

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.config.cwd,
            env=env,
        )

    def request(self, method, params=None):
        self.start()

        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError(f"No se pudo iniciar el servidor MCP {self.server_name}")

        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }

            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()

            while True:
                line = self.process.stdout.readline()
                if not line:
                    stderr_output = ""
                    if self.process.stderr is not None:
                        stderr_output = self.process.stderr.read() or ""
                    raise RuntimeError(
                        f"El servidor MCP {self.server_name} no respondió. {stderr_output.strip()}"
                    )

                data = json.loads(line)
                if data.get("id") != request_id:
                    continue

                if "error" in data:
                    raise RuntimeError(data["error"].get("message", "Error MCP desconocido"))

                return data.get("result", {})

    def close(self):
        if self.process is None:
            return

        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
            if self.process.stdout is not None:
                self.process.stdout.close()
            if self.process.stderr is not None:
                self.process.stderr.close()
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except Exception:
                    self.process.kill()
            self.process = None


def _normalize_server_config(config):
    if isinstance(config, MCPServerConfig):
        return config

    if not isinstance(config, dict):
        raise TypeError("La configuración MCP debe ser un diccionario")

    command = config.get("command") or []
    args = config.get("args") or []
    if isinstance(command, str):
        command = [command]
    if isinstance(args, str):
        args = [args]

    return MCPServerConfig(
        command=list(command),
        args=list(args),
        cwd=config.get("cwd"),
        env=dict(config.get("env") or {}),
        transport=config.get("transport", "stdio"),
    )


class MCPClient:
    def __init__(self):
        self._servers = {}
        self._connections = {}
        self._tool_to_server = {}
        self._discovered_tools = []

    def register_server(self, name, config):
        self._servers[name] = _normalize_server_config(config)

    def list_servers(self):
        return dict(self._servers)

    def discover_tools(self):
        discovered = []

        for server_name, config in self._servers.items():
            connection = self._connections.get(server_name)
            if connection is None:
                connection = _MCPConnection(server_name, config)
                self._connections[server_name] = connection

            try:
                try:
                    connection.request(
                        "initialize",
                        {
                            "protocolVersion": "2024-11-05",
                            "clientInfo": {"name": "Yiujarvis", "version": "1.0.0"},
                            "capabilities": {},
                        },
                    )
                except Exception:
                    pass

                result = connection.request("tools/list", {})
                tools = result.get("tools", []) if isinstance(result, dict) else []

                for tool in tools:
                    if not isinstance(tool, dict):
                        continue

                    definition = MCPToolDefinition(
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        schema=tool.get("inputSchema", {"type": "object", "properties": {}}),
                        server_name=server_name,
                        risk=tool.get("risk", "safe"),
                        capabilities=list(tool.get("capabilities", []) or []),
                        metadata=tool,
                    )
                    discovered.append(definition)
                    self._tool_to_server[definition.name] = server_name
            except Exception:
                log_exception(f"Error descubriendo tools MCP en {server_name}")

        self._discovered_tools = discovered
        return discovered

    def invoke(self, tool_name, arguments):
        server_name = self._tool_to_server.get(tool_name)
        if server_name is None:
            raise KeyError(f"No existe la tool MCP {tool_name}")

        connection = self._connections.get(server_name)
        if connection is None:
            raise RuntimeError(f"No hay conexión activa para {server_name}")

        result = connection.request("tools/call", {"name": tool_name, "arguments": arguments})

        if isinstance(result, dict):
            if "content" in result and isinstance(result["content"], list):
                texts = []
                for block in result["content"]:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            texts.append(str(block.get("text", "")))
                        elif "text" in block:
                            texts.append(str(block.get("text", "")))
                if texts:
                    return "\n".join(texts)

            if "text" in result:
                return str(result["text"])

        return json.dumps(result, ensure_ascii=False)

    def close(self):
        for connection in self._connections.values():
            connection.close()

        self._connections.clear()
        self._tool_to_server.clear()
        self._discovered_tools.clear()


def create_tool_from_mcp_definition(definition, client):
    if not isinstance(definition, MCPToolDefinition):
        raise TypeError("Se esperaba una definición MCPToolDefinition")

    def _runner(**kwargs):
        return client.invoke(definition.name, kwargs)

    return _runner