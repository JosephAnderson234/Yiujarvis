import json

from src.config import get_model_config
from src.tools import close_program, get_weather, list_running_processes, open_app, save_user_preference


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Obtiene el clima actual",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Abre una aplicación",
            "parameters": {
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_processes",
            "description": "Lista las apps y ventanas abiertas de Windows",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 30},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_program",
            "description": "Cierra una app abierta de Windows por nombre o ventana",
            "parameters": {
                "type": "object",
                "properties": {
                    "process_name": {"type": "string"},
                },
                "required": ["process_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_preference",
            "description": "Guarda información importante del usuario",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "close_program": close_program,
    "get_weather": get_weather,
    "list_running_processes": list_running_processes,
    "open_app": open_app,
    "save_user_preference": save_user_preference,
}


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


def Yiujarvis(initial_memory, provider="githubmodel"):
    model_config = get_model_config(provider)
    client = model_config["client"]
    model_name = model_config["model_name"]

    messages = [
        {
            "role": "system",
            "content": f"""
Eres Yiujarvis, un asistente personal inteligente.

Objetivos:
- Ayudar con productividad, información y automatización
- Usar herramientas cuando sea necesario
- Poder revisar apps abiertas de Windows y cerrar programas cuando el usuario lo pida
- Guardar información útil del usuario usando herramientas

Memoria actual del usuario:
{initial_memory}
""",
        }
    ]

    while True:
        user_input = input("\n🧑 Tú: ")
        if user_input.lower() in ["salir", "exit"]:
            break

        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

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
                arguments = json.loads(tool_call.function.arguments)
                function_to_call = AVAILABLE_FUNCTIONS[function_name]
                result = function_to_call(**arguments)

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
            messages.append({"role": "assistant", "content": final_message})
        else:
            if model_config["provider"] == "groq":
                print("\n🤖 Yiujarvis: ", end="")
                streamed_message = stream_groq_response(client, model_name, messages)
                messages.append({"role": "assistant", "content": streamed_message})
            else:
                print(f"\n🤖 Yiujarvis: {message.content}")
                messages.append({"role": "assistant", "content": message.content})