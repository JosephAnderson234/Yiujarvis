import logging
from dataclasses import dataclass
from typing import Any, Callable

from src.error_logger import ensure_error_logging, log_error, log_exception


ensure_error_logging()
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict
    func: Callable[..., Any]


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        self._tools[tool.name] = tool
        return tool

    def get(self, name):
        return self._tools.get(name)

    def get_available_tools(self):
        tools = []

        for tool in self._tools.values():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.schema,
                    },
                }
            )

        return tools

    def execute(self, name, **kwargs):
        tool = self.get(name)

        if tool is None:
            log_error(f"Intento de ejecutar una tool inexistente: {name}")
            return f"No existe la tool {name}"

        try:
            return tool.func(**kwargs)
        except Exception as exc:
            log_exception(f"Error ejecutando tool {name}")
            return f"No se pudo ejecutar {name}: {exc}"