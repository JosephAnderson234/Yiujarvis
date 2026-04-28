import logging
from dataclasses import dataclass
from dataclasses import field
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
    risk: str = "safe"
    source: str = "local"
    keywords: list[str] = field(default_factory=list)


class ToolRegistry:
    def __init__(self, confirm_callback=None):
        self._tools = {}
        self._confirm_callback = confirm_callback

    def register(self, tool):
        self._tools[tool.name] = tool
        return tool

    def register_external_tool(
        self,
        name,
        description,
        schema,
        func,
        risk="safe",
        source="external",
        keywords=None,
    ):
        return self.register(
            Tool(
                name=name,
                description=description,
                schema=schema,
                func=func,
                risk=risk,
                source=source,
                keywords=list(keywords or []),
            )
        )

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

    def list_tool_names(self):
        return [tool.name for tool in self._tools.values()]

    def list_tools(self):
        return list(self._tools.values())

    def set_confirmation_callback(self, callback):
        self._confirm_callback = callback

    def _requires_confirmation(self, tool):
        return tool.risk.lower() in {"dangerous", "sensitive"}

    def _confirm(self, tool, kwargs):
        if self._confirm_callback is None:
            return True

        return bool(self._confirm_callback(tool, kwargs))

    def execute(self, name, **kwargs):
        tool = self.get(name)

        if tool is None:
            log_error(f"Intento de ejecutar una tool inexistente: {name}")
            return f"No existe la tool {name}"

        if kwargs.pop("dry_run", False):
            return f"[dry-run] {name} no se ejecutó"

        if self._requires_confirmation(tool) and not self._confirm(tool, kwargs):
            return f"Ejecución cancelada para {name}"

        try:
            return tool.func(**kwargs)
        except Exception as exc:
            log_exception(f"Error ejecutando tool {name}")
            return f"No se pudo ejecutar {name}: {exc}"