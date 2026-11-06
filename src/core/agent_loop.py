import json
import logging
from itertools import chain
from datetime import datetime

from src.config import get_model_config
from src.error_logger import ensure_error_logging, log_exception
from src.intent import is_direct_command, is_shutdown_command
from src.memory_store import MemorySession, build_memory_context
from src.core.tool_registry import Tool, ToolRegistry
from src.tools import close_program, get_weather, list_running_processes, open_app, save_user_preference
from src.plugins import load_plugins
from src.planner.executor import PlanExecutor
from src.planner.planner import Planner
from src.mcp.client import MCPClient
from src.mcp.loader import load_mcp_tools
from src.mcp.registry import MCPRegistry
from src.terminal_ui import (
    Spinner,
    print_assistant,
    print_assistant_prefix,
    print_notice,
    print_plan,
    print_tool_call,
    print_warning,
    prompt_user,
)


ensure_error_logging()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8
MAX_TOOL_RESULT_CHARS = 4000
MAX_CONTEXT_MESSAGES = 40
KEEP_RECENT_MESSAGES = 16
DIRECT_INTENTS = {"open_app", "close_program"}


def build_tool_registry(memory_session=None):
    def confirm_sensitive_action(tool, kwargs):
        print(f"\n⚠️ La tool {tool.name} se considera {tool.risk}. Argumentos: {kwargs}")
        answer = read_user_input("Confirmar ejecución? (y/n): ")
        return (answer or "").strip().lower() in {"y", "yes", "s", "si", "sí"}

    registry = ToolRegistry(confirm_callback=confirm_sensitive_action)

    registry.register(
        Tool(
            name="get_weather",
            description=(
                "Obtiene el clima actual y el pronóstico de hoy. Si no se indica ciudad, "
                "usa la ubicación aproximada del usuario."
            ),
            schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Ciudad a consultar, por ejemplo 'Lima'"},
                },
            },
            func=get_weather,
            risk="safe",
            keywords=["clima", "tiempo", "weather", "temperatura", "lluvia"],
            capabilities=["info"],
        )
    )
    registry.register(
        Tool(
            name="open_app",
            description="Abre una aplicación instalada, una URL o una página de configuración de Windows",
            schema={
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
            func=open_app,
            risk="dangerous",
            keywords=["abrir", "abre", "open", "launch", "iniciar", "app", "programa"],
        )
    )
    registry.register(
        Tool(
            name="list_running_processes",
            description="Lista las apps y ventanas abiertas de Windows",
            schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 30},
                },
            },
            func=list_running_processes,
            risk="safe",
            keywords=["procesos", "ventanas", "apps", "abiertas", "running", "lista"],
        )
    )
    registry.register(
        Tool(
            name="close_program",
            description="Cierra una app abierta de Windows por nombre o ventana",
            schema={
                "type": "object",
                "properties": {
                    "process_name": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["process_name"],
            },
            func=close_program,
            risk="dangerous",
            keywords=["cerrar", "cierra", "close", "terminar", "mata", "kill"],
        )
    )

    preference_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"],
    }
    preference_description = "Guarda una preferencia clave/valor del usuario (nombre, ciudad, apps favoritas...)"
    preference_keywords = ["guarda", "guardar", "recuerda", "preferencia", "memo", "anota"]

    if memory_session is None:
        registry.register(
            Tool(
                name="save_user_preference",
                description=preference_description,
                schema=preference_schema,
                func=save_user_preference,
                risk="safe",
                keywords=preference_keywords,
                capabilities=["memory"],
            )
        )
    else:
        def save_preference_in_session(key, value):
            memory_session.set_preference(key, value)
            return f"Guardado: {key} = {value}"

        def remember_fact(fact):
            memory_session.add_fact(fact)
            return f"Recordaré: {fact}"

        registry.register(
            Tool(
                name="save_user_preference",
                description=preference_description,
                schema=preference_schema,
                func=save_preference_in_session,
                risk="safe",
                keywords=preference_keywords,
                capabilities=["memory"],
            )
        )
        registry.register(
            Tool(
                name="remember_fact",
                description=(
                    "Guarda un hecho útil sobre el usuario o su contexto para recordarlo en futuras "
                    "conversaciones (proyectos, gustos, rutinas, personas importantes)"
                ),
                schema={
                    "type": "object",
                    "properties": {"fact": {"type": "string"}},
                    "required": ["fact"],
                },
                func=remember_fact,
                risk="safe",
                keywords=["recuerda", "recordar", "anota", "dato"],
                capabilities=["memory"],
            )
        )

    load_plugins(registry)

    mcp_client = MCPClient()
    mcp_registry = MCPRegistry()
    load_mcp_tools(registry, client=mcp_client, mcp_registry=mcp_registry)
    registry.mcp_client = mcp_client

    return registry


def build_system_prompt(memory, relevant_memory=None, ranked_tools=None, session_summary=""):
    memory_context = build_memory_context(memory)
    relevant_memory = relevant_memory or []
    ranked_tools = ranked_tools or []

    relevant_memory_block = "\n".join(
        f"- {item.get('source')}: {item.get('key', '')} {item.get('value', '')}".rstrip()
        for item in relevant_memory[:5]
    ) or "- ninguna"

    ranked_tools_block = "\n".join(
        f"- {item.get('tool')}: {item.get('score')}"
        for item in ranked_tools[:5]
    ) or "- ninguna"

    now = datetime.now().astimezone()

    return f"""
Eres Yiujarvis, el asistente personal del usuario en su PC con Windows, al estilo de J.A.R.V.I.S.
Eres eficiente, cercano, con un toque de humor seco, y respondes en español.

Fecha y hora actual: {now.strftime("%A %d/%m/%Y %H:%M")} ({now.tzname()})

Cómo trabajas:
- Eres un agente: para cumplir un pedido puedes llamar varias tools seguidas, revisar sus resultados y decidir el siguiente paso.
- Usa tools cuando aporten datos reales o ejecuten acciones; no inventes resultados que una tool puede darte.
- Si una tool falla, intenta corregir los argumentos o usa otra alternativa antes de rendirte.
- Cuando el usuario comparta algo útil de sí mismo (gustos, proyectos, ciudad, rutinas), guárdalo con save_user_preference o remember_fact sin que te lo pida.
- Responde breve y directo: primero el resultado, luego detalles solo si hacen falta.

Memoria del usuario:
{memory_context}

Resumen de lo hablado antes en esta sesión:
{session_summary or "- nada todavía"}

Memoria relevante para este mensaje:
{relevant_memory_block}

Tools sugeridas por ranking para este mensaje:
{ranked_tools_block}
"""


def stream_completion(client, model_name, messages, tools=None, tool_choice="auto"):
    """Hace streaming de la respuesta imprimiendo el texto y acumulando tool calls parciales."""
    request = {"model": model_name, "messages": messages, "stream": True}
    if tools:
        request["tools"] = tools
        request["tool_choice"] = tool_choice

    with Spinner("Esperando respuesta"):
        stream = iter(client.chat.completions.create(**request))
        first_chunk = next(stream, None)

    content_parts = []
    tool_calls = {}
    started = False

    for chunk in chain((first_chunk,), stream):
        if chunk is None:
            continue
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        if delta is None:
            continue

        text = getattr(delta, "content", None)
        if text:
            if not started:
                print_assistant_prefix()
                started = True
            print(text, end="", flush=True)
            content_parts.append(text)

        for call_delta in getattr(delta, "tool_calls", None) or []:
            index = call_delta.index if call_delta.index is not None else len(tool_calls)
            entry = tool_calls.setdefault(
                index,
                {"id": f"call_{index}", "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if call_delta.id:
                entry["id"] = call_delta.id

            function = call_delta.function
            if function is not None:
                if function.name:
                    entry["function"]["name"] = function.name
                if function.arguments:
                    entry["function"]["arguments"] += function.arguments

    if started:
        print()

    if not content_parts and not tool_calls:
        raise RuntimeError(
            f"El proveedor devolvió una respuesta vacía para {model_name}; revisa su sesión o configuración."
        )

    return "".join(content_parts), [tool_calls[index] for index in sorted(tool_calls)]


def _format_tool_result(result):
    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False, default=str)

    if len(result) > MAX_TOOL_RESULT_CHARS:
        return result[:MAX_TOOL_RESULT_CHARS] + "\n...[resultado truncado]"

    return result


def execute_tool_call(registry, tool_call):
    function_name = tool_call["function"]["name"]
    raw_arguments = tool_call["function"]["arguments"] or "{}"

    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        log_exception(f"Argumentos inválidos para la tool {function_name}")
        return f"Argumentos inválidos (JSON mal formado) para {function_name}: {raw_arguments}"

    if not isinstance(arguments, dict):
        return f"Los argumentos de {function_name} deben ser un objeto JSON"

    print_tool_call(function_name, arguments)
    tool = registry.get(function_name)
    if tool is not None and tool.risk.lower() in {"dangerous", "sensitive"}:
        return _format_tool_result(registry.execute(function_name, **arguments))
    with Spinner(f"Ejecutando {function_name}"):
        return _format_tool_result(registry.execute(function_name, **arguments))


def run_agent_turn(client, model_name, messages, registry):
    """Loop ReAct: el modelo llama tools, ve sus resultados y repite hasta tener una respuesta final."""
    tools = registry.get_available_tools()

    for _ in range(MAX_TOOL_ROUNDS):
        content, tool_calls = stream_completion(client, model_name, messages, tools=tools)

        if not tool_calls:
            messages.append({"role": "assistant", "content": content})
            return content

        messages.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})

        for tool_call in tool_calls:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": execute_tool_call(registry, tool_call),
                }
            )

    print_notice(f"Llegué al límite de {MAX_TOOL_ROUNDS} rondas de tools; respondo con lo que tengo.")
    content, _ = stream_completion(client, model_name, messages, tools=tools, tool_choice="none")
    messages.append({"role": "assistant", "content": content})
    return content


def _render_for_summary(message):
    role = message.get("role")

    if role == "tool":
        return f"[resultado de tool] {str(message.get('content', ''))[:300]}"

    if message.get("tool_calls"):
        calls = ", ".join(
            f"{call['function']['name']}({call['function']['arguments']})" for call in message["tool_calls"]
        )
        return f"assistant (llamó tools): {calls}"

    return f"{role}: {message.get('content', '')}"


def compact_conversation(client, model_name, messages, session_summary):
    """Si la conversación crece demasiado, resume lo antiguo y conserva solo los turnos recientes."""
    conversation = messages[1:]
    if len(conversation) <= MAX_CONTEXT_MESSAGES:
        return session_summary

    # El corte debe caer en un mensaje de usuario para no separar tool_calls de sus resultados.
    cut = len(conversation) - KEEP_RECENT_MESSAGES
    while cut < len(conversation) and conversation[cut].get("role") != "user":
        cut += 1

    if cut >= len(conversation):
        return session_summary

    dropped = conversation[:cut]
    transcript = "\n".join(_render_for_summary(message) for message in dropped)

    try:
        with Spinner("Resumiendo conversación"):
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Resume en español, en máximo 10 viñetas, los datos, decisiones, resultados de "
                            "acciones y tareas pendientes de esta conversación. Integra el resumen previo."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Resumen previo:\n{session_summary or '- ninguno'}\n\nConversación:\n{transcript}",
                    },
                ],
            )
        session_summary = response.choices[0].message.content or session_summary
    except Exception:
        log_exception("No se pudo resumir la conversación")

    del messages[1 : 1 + cut]
    return session_summary


def run_direct_command(planner, executor, user_input):
    with Spinner("Preparando plan"):
        plan = planner.build_plan(user_input)

    if plan.intent not in DIRECT_INTENTS:
        return None

    if plan.steps:
        print_plan("Plan detectado:", plan.steps)

    for note in plan.notes:
        print_notice(note)

    results = executor.run(plan)
    summary = " | ".join(results) if results else "No había acciones que ejecutar."
    print_assistant(summary)
    return summary


def read_user_input(prompt):
    try:
        return input(prompt)
    except EOFError:
        return None
    except KeyboardInterrupt:
        return None


def shutdown_session(memory_session, message="Apagándome y guardando memoria."):
    memory_session.save()
    print_warning(message)


def Yiujarvis(memory, provider="codex", registry=None):
    memory_session = memory if isinstance(memory, MemorySession) else MemorySession(memory)
    model_config = get_model_config(provider)
    client = model_config["client"]
    model_name = model_config["model_name"]
    registry = registry or build_tool_registry(memory_session)
    planner = Planner(registry=registry, memory_store=memory_session.data)
    executor = PlanExecutor(registry)
    session_summary = ""

    messages = [{"role": "system", "content": build_system_prompt(memory_session.data)}]

    try:
        while True:
            user_input = read_user_input("\n" + prompt_user())
            if user_input is None:
                print_warning("Sesión cerrada.")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if is_shutdown_command(user_input):
                shutdown_session(memory_session)
                break

            memory_session.append_history("user", user_input)
            planner.memory_store = memory_session.data

            # Atajo determinista: órdenes cortas tipo "abre X y Y" no necesitan al LLM.
            if is_direct_command(user_input):
                summary = run_direct_command(planner, executor, user_input)
                if summary is not None:
                    messages.append({"role": "user", "content": user_input})
                    messages.append({"role": "assistant", "content": summary})
                    memory_session.append_history("assistant", summary)
                    memory_session.save()
                    continue

            with Spinner("Analizando solicitud"):
                hints = planner.build_plan(user_input).context
            session_summary = compact_conversation(client, model_name, messages, session_summary)
            messages[0]["content"] = build_system_prompt(
                memory_session.data,
                hints.get("relevant_memory", []),
                hints.get("ranked_tools", []),
                session_summary,
            )

            turn_start = len(messages)
            messages.append({"role": "user", "content": user_input})

            try:
                final_message = run_agent_turn(client, model_name, messages, registry)
            except Exception as exc:
                log_exception("No se pudo completar el turno con el modelo")
                print_warning(f"No se pudo consultar el modelo: {exc}")
                del messages[turn_start:]
                continue

            memory_session.append_history("assistant", final_message)
            memory_session.save()
    finally:
        memory_session.save()
        mcp_client = getattr(registry, "mcp_client", None)
        if mcp_client is not None:
            mcp_client.close()
