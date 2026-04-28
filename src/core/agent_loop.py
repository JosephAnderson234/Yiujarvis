import json
import logging
from collections import deque

from src.config import get_model_config
from src.error_logger import ensure_error_logging, log_exception
from src.intent import classify_intent
from src.memory_store import append_history, build_memory_context, load_memory, save_memory
from src.core.tool_registry import Tool, ToolRegistry
from src.tools import close_program, get_weather, list_running_processes, open_app, save_user_preference
from src.plugins import load_plugins
from src.planner.executor import PlanExecutor
from src.planner.planner import Planner
from src.terminal_ui import print_assistant, print_notice, print_plan, print_warning, prompt_user


ensure_error_logging()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def build_tool_registry():
    def confirm_sensitive_action(tool, kwargs):
        print(f"\n⚠️ La tool {tool.name} se considera {tool.risk}. Argumentos: {kwargs}")
        answer = read_user_input("Confirmar ejecución? (y/n): ")
        return (answer or "").strip().lower() in {"y", "yes", "s", "si", "sí"}

    registry = ToolRegistry(confirm_callback=confirm_sensitive_action)

    registry.register(
        Tool(
            name="get_weather",
            description="Obtiene el clima actual",
            schema={"type": "object", "properties": {}},
            func=get_weather,
            risk="safe",
        )
    )
    registry.register(
        Tool(
            name="open_app",
            description="Abre una aplicación",
            schema={
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
            func=open_app,
            risk="dangerous",
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
        )
    )
    registry.register(
        Tool(
            name="save_user_preference",
            description="Guarda información importante del usuario",
            schema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
            func=save_user_preference,
            risk="safe",
        )
    )

    load_plugins(registry)

    return registry


def build_system_prompt(initial_memory, recent_messages, registry):
    tool_names = registry.list_tool_names()
    memory_context = build_memory_context(initial_memory, recent_messages)

    return f"""
Eres Yiujarvis, un asistente personal inteligente.

Objetivos:
- Ayudar con productividad, información y automatización
- Usar herramientas cuando sea necesario
- Detectar cuando el usuario pide acciones simples y ejecutar planes directos si conviene
- Poder revisar apps abiertas de Windows y cerrar programas cuando el usuario lo pida
- Guardar información útil del usuario usando herramientas

Memoria actual del usuario:
{memory_context}

Herramientas disponibles:
{", ".join(tool_names)}

Si el usuario pide abrir o cerrar varias apps, prioriza acciones directas y responde de forma breve.
"""


def run_planned_actions(registry, plan):
    results = []

    if not plan.get("steps"):
        return results

    print_plan("Plan detectado:", plan["steps"])

    for step in plan["steps"]:
        tool_name = step.get("tool")
        arguments = step.get("arguments", {})
        result = registry.execute(tool_name, **arguments)
        results.append(result)
        print_notice(result)

    return results


def stream_groq_response(client, model_name, messages):
    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )

    parts = []
    for chunk in completion:
        content = chunk.choices[0].delta.content or ""
        if content:
            print(content, end="", flush=True)
            parts.append(content)

    print()
    return "".join(parts)


def read_user_input(prompt):
    try:
        return input(prompt)
    except EOFError:
        return None
    except KeyboardInterrupt:
        return None


def persist_state(memory):
    save_memory(memory)


def shutdown_session(memory, message="Apagándome y guardando memoria."):
    persist_state(memory)
    print_warning(message)


def Yiujarvis(initial_memory, provider="githubmodel"):
    model_config = get_model_config(provider)
    client = model_config["client"]
    model_name = model_config["model_name"]
    registry = build_tool_registry()
    planner = Planner()
    executor = PlanExecutor(registry)
    recent_messages = deque(maxlen=10)

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(initial_memory, recent_messages, registry),
        }
    ]

    try:
        while True:
            user_input = read_user_input("\n" + prompt_user())
            if user_input is None:
                print_warning("Sesión cerrada.")
                break

            if classify_intent(user_input) == "shutdown":
                shutdown_session(initial_memory)
                break

            recent_messages.append({"role": "user", "content": user_input})
            append_history(initial_memory, "user", user_input)

            messages[0]["content"] = build_system_prompt(initial_memory, recent_messages, registry)

            plan = planner.build_plan(user_input)

            if plan.steps or plan.notes:
                print_plan("Plan detectado:", plan.steps)

            if plan.notes:
                for note in plan.notes:
                    print_notice(note)

            if plan.intent in {"open_app", "close_program"}:
                results = executor.run(plan)
                summary = " | ".join(results) if results else "No se ejecutó ninguna acción."
                if results:
                    print_assistant(summary)
                    recent_messages.append({"role": "assistant", "content": summary})
                    append_history(initial_memory, "assistant", summary)
                    persist_state(initial_memory)
                    messages.append({"role": "assistant", "content": summary})
                else:
                    fallback = "No había acciones que ejecutar."
                    print_notice(fallback)
                    recent_messages.append({"role": "assistant", "content": fallback})
                    append_history(initial_memory, "assistant", fallback)
                    persist_state(initial_memory)
                    messages.append({"role": "assistant", "content": fallback})
                continue

            messages.append({"role": "user", "content": user_input})

            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=registry.get_available_tools(),
                    tool_choice="auto",
                )
            except Exception as exc:
                log_exception("No se pudo consultar el modelo")
                print_warning(f"No se pudo consultar el modelo: {exc}")
                continue

            message = response.choices[0].message

            if message.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [tool_call.model_dump() for tool_call in message.tool_calls],
                    }
                )

                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        log_exception(f"Argumentos inválidos para la tool {function_name}")
                        arguments = {}

                    result = registry.execute(function_name, **arguments)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )

                print("\n🤖 Yiujarvis: ", end="")
                if model_config["provider"] == "groq":
                    final_message = stream_groq_response(client, model_name, messages)
                else:
                    second_response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                    )
                    final_message = second_response.choices[0].message.content
                    print(final_message)

                recent_messages.append({"role": "assistant", "content": final_message})
                append_history(initial_memory, "assistant", final_message)
                persist_state(initial_memory)
                messages.append({"role": "assistant", "content": final_message})
            else:
                if model_config["provider"] == "groq":
                    print("\n🤖 Yiujarvis: ", end="")
                    streamed_message = stream_groq_response(client, model_name, messages)
                    recent_messages.append({"role": "assistant", "content": streamed_message})
                    append_history(initial_memory, "assistant", streamed_message)
                    persist_state(initial_memory)
                    messages.append({"role": "assistant", "content": streamed_message})
                else:
                    print_assistant(message.content)
                    recent_messages.append({"role": "assistant", "content": message.content})
                    append_history(initial_memory, "assistant", message.content)
                    persist_state(initial_memory)
                    messages.append({"role": "assistant", "content": message.content})
    finally:
        persist_state(initial_memory)