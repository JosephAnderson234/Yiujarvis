import json
import logging
from collections import deque

from src.config import get_model_config
from src.error_logger import ensure_error_logging, log_exception
from src.memory_store import append_history, build_memory_context, load_memory, save_memory
from src.core.tool_registry import Tool, ToolRegistry
from src.tools import close_program, get_weather, list_running_processes, open_app, save_user_preference


ensure_error_logging()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def build_tool_registry():
    registry = ToolRegistry()

    registry.register(
        Tool(
            name="get_weather",
            description="Obtiene el clima actual",
            schema={"type": "object", "properties": {}},
            func=get_weather,
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
                },
                "required": ["process_name"],
            },
            func=close_program,
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
        )
    )

    return registry


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


def Yiujarvis(initial_memory, provider="githubmodel"):
    model_config = get_model_config(provider)
    client = model_config["client"]
    model_name = model_config["model_name"]
    registry = build_tool_registry()
    recent_messages = deque(maxlen=10)

    messages = [
        {
            "role": "system",
            "content": "",
        }
    ]

    system_prompt = """
Eres Yiujarvis, un asistente personal inteligente.

Objetivos:
- Ayudar con productividad, información y automatización
- Usar herramientas cuando sea necesario
- Poder revisar apps abiertas de Windows y cerrar programas cuando el usuario lo pida
- Guardar información útil del usuario usando herramientas

Memoria actual del usuario:
{build_memory_context(initial_memory, recent_messages)}
"""

    messages[0]["content"] = system_prompt

    while True:
        user_input = read_user_input("\n🧑 Tú: ")
        if user_input is None:
            print("\n🤖 Yiujarvis: Sesión cerrada.")
            break

        if user_input.lower() in ["salir", "exit"]:
            break

        recent_messages.append({"role": "user", "content": user_input})
        append_history(initial_memory, "user", user_input)

        messages[0]["content"] = f"""
Eres Yiujarvis, un asistente personal inteligente.

Objetivos:
- Ayudar con productividad, información y automatización
- Usar herramientas cuando sea necesario
- Poder revisar apps abiertas de Windows y cerrar programas cuando el usuario lo pida
- Guardar información útil del usuario usando herramientas

Memoria actual del usuario:
{build_memory_context(initial_memory, recent_messages)}
"""

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
            print(f"\n🤖 Yiujarvis: No se pudo consultar el modelo: {exc}")
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
            save_memory(initial_memory)
            messages.append({"role": "assistant", "content": final_message})
        else:
            if model_config["provider"] == "groq":
                print("\n🤖 Yiujarvis: ", end="")
                streamed_message = stream_groq_response(client, model_name, messages)
                recent_messages.append({"role": "assistant", "content": streamed_message})
                append_history(initial_memory, "assistant", streamed_message)
                save_memory(initial_memory)
                messages.append({"role": "assistant", "content": streamed_message})
            else:
                print(f"\n🤖 Yiujarvis: {message.content}")
                recent_messages.append({"role": "assistant", "content": message.content})
                append_history(initial_memory, "assistant", message.content)
                save_memory(initial_memory)
                messages.append({"role": "assistant", "content": message.content})