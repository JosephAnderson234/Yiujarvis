"""Chat-completions-compatible bridge for subscription-authenticated agent CLIs."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


MAX_CLI_SECONDS = 180
MAX_TOOL_CALLS = 5
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "string"},
                },
                "required": ["name", "arguments"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["content", "tool_calls"],
    "additionalProperties": False,
}

ENVIRONMENT_KEYS = {
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "USERPROFILE",
    "HOMEDRIVE", "HOMEPATH", "HOME", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
    "TEMP", "TMP", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "LANG", "LC_ALL",
}


def _cli_environment():
    """Keep OS/auth paths while omitting API keys and unrelated process secrets."""
    return {key: value for key, value in os.environ.items() if key.upper() in ENVIRONMENT_KEYS}


def _prompt(messages, tools, tool_choice):
    rules = (
        "Eres el motor de conversación de Yiujarvis. Sigue el mensaje de sistema del historial. "
        "Responde en español mediante un objeto JSON con content (texto) y tool_calls (lista). "
        "Si necesitas una herramienta, usa solo las herramientas ofrecidas, indica su nombre y "
        "argumentos como una cadena que contiene un objeto JSON. No afirmes que ejecutaste una herramienta antes de recibir "
        "su resultado en el historial. Cada respuesta puede pedir como máximo cinco herramientas. "
        "No uses herramientas propias de la CLI ni leas archivos del entorno."
    )
    if tool_choice == "none" or not tools:
        rules += " Esta respuesta debe ser final: tool_calls debe ser una lista vacía."
    return "\n\n".join((
        rules,
        "HISTORIAL (JSON):\n" + json.dumps(messages, ensure_ascii=False, default=str),
        "HERRAMIENTAS DISPONIBLES (JSON):\n" + json.dumps(tools or [], ensure_ascii=False, default=str),
    ))


def _run_cli(provider, prompt):
    executable = shutil.which(provider)
    if not executable:
        raise RuntimeError(f"No encuentro la CLI '{provider}' en PATH. Instálala y abre una sesión en ella.")

    with tempfile.TemporaryDirectory(prefix="yiujarvis-cli-") as directory:
        workdir = Path(directory)
        if provider == "codex":
            schema_path = workdir / "response.schema.json"
            answer_path = workdir / "answer.json"
            schema_path.write_text(json.dumps(RESPONSE_SCHEMA), encoding="utf-8")
            command = [
                executable, "exec", "--ignore-user-config", "--ephemeral",
                "--sandbox", "read-only", "--skip-git-repo-check",
                "--cd", directory, "--output-schema", str(schema_path),
                "--output-last-message", str(answer_path), "-",
            ]
        elif provider == "claude":
            command = [
                executable, "-p", "Sigue las instrucciones recibidas por stdin.",
                "--output-format", "json", "--json-schema", json.dumps(RESPONSE_SCHEMA),
                "--tools", "", "--safe-mode", "--strict-mcp-config",
                "--no-session-persistence", "--permission-mode", "manual",
                "--permission-prompts", "none",
            ]
        else:
            raise ValueError(f"Proveedor CLI desconocido: {provider}")

        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            result = subprocess.run(
                command, input=prompt, text=True, capture_output=True,
                cwd=directory, env=_cli_environment(), timeout=MAX_CLI_SECONDS,
                encoding="utf-8", errors="replace", creationflags=flags,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{provider} tardó más de {MAX_CLI_SECONDS} segundos") from exc

        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[-1000:]
            raise RuntimeError(f"{provider} CLI falló: {detail or f'código {result.returncode}'}")

        if provider == "codex":
            if not answer_path.exists():
                raise RuntimeError("Codex no guardó la respuesta final")
            raw = answer_path.read_text(encoding="utf-8")
            return json.loads(raw)

        envelope = json.loads(result.stdout)
        if envelope.get("is_error"):
            raise RuntimeError(f"Claude CLI falló: {str(envelope.get('result', 'sin detalle'))[:1000]}")
        payload = envelope.get("structured_output")
        if payload is None:
            raise RuntimeError("Claude no devolvió una respuesta estructurada")
        return payload


def _validated_response(payload, tools, tool_choice):
    if not isinstance(payload, dict) or not isinstance(payload.get("content"), str):
        raise RuntimeError("La CLI devolvió una respuesta con formato inválido")
    calls = payload.get("tool_calls")
    if not isinstance(calls, list):
        raise RuntimeError("La CLI no devolvió la lista de herramientas")
    if len(calls) > MAX_TOOL_CALLS:
        raise RuntimeError("La CLI solicitó demasiadas herramientas")
    allowed = {item["function"]["name"] for item in tools or []}
    if tool_choice == "none" or not tools:
        calls = []
    normalized = []
    for index, call in enumerate(calls):
        if not isinstance(call, dict) or call.get("name") not in allowed or not isinstance(call.get("arguments"), str):
            raise RuntimeError("La CLI solicitó una herramienta o argumentos inválidos")
        try:
            arguments = json.loads(call["arguments"])
        except json.JSONDecodeError as exc:
            raise RuntimeError("La CLI devolvió argumentos JSON inválidos") from exc
        if not isinstance(arguments, dict):
            raise RuntimeError("La CLI devolvió argumentos que no son un objeto")
        normalized.append(SimpleNamespace(
            index=index,
            id=f"cli_call_{index}",
            function=SimpleNamespace(
                name=call["name"],
                arguments=json.dumps(arguments, ensure_ascii=False),
            ),
        ))
    if not payload["content"] and not normalized:
        raise RuntimeError("La CLI devolvió una respuesta vacía")
    return payload["content"], normalized


class CLICompletions:
    def __init__(self, provider):
        self.provider = provider

    def create(self, *, model, messages, stream=False, tools=None, tool_choice="auto"):
        del model
        payload = _run_cli(self.provider, _prompt(messages, tools, tool_choice))
        content, calls = _validated_response(payload, tools, tool_choice)
        choice = SimpleNamespace(
            delta=SimpleNamespace(content=content, tool_calls=calls),
            message=SimpleNamespace(content=content),
        )
        response = SimpleNamespace(choices=[choice])
        return iter([response]) if stream else response


class CLIAgentClient:
    def __init__(self, provider):
        self.chat = SimpleNamespace(completions=CLICompletions(provider))
