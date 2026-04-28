# MCP Avanzado en Yiujarvis

Este documento explica cómo usar MCP en Yiujarvis de forma práctica y avanzada, según la implementación actual del proyecto.

## Qué hace MCP aquí

En este proyecto, MCP sirve para registrar tools externas como si fueran locales. Yiujarvis levanta servidores MCP locales por `stdio`, pregunta qué tools exponen y las añade al `ToolRegistry`.

El flujo real es:

1. Se lee `mcp_servers.json`.
2. `MCPClient` registra cada servidor.
3. `MCPClient` abre el proceso local del servidor MCP.
4. Yiujarvis envía `initialize` y `tools/list`.
5. Cada tool descubierta se registra en el registry general.
6. Cuando el planner o el LLM elige una tool MCP, `tools/call` la ejecuta.

## Arquitectura actual

Los módulos relevantes son:

- [src/mcp/client.py](../src/mcp/client.py)
- [src/mcp/loader.py](../src/mcp/loader.py)
- [src/mcp/registry.py](../src/mcp/registry.py)
- [src/core/tool_registry.py](../src/core/tool_registry.py)
- [src/planner/planner.py](../src/planner/planner.py)

### `MCPClient`

`MCPClient` gestiona:

- Registro de servidores.
- Inicio de procesos locales.
- Peticiones JSON-RPC por `stdin/stdout`.
- Descubrimiento de tools con `tools/list`.
- Ejecución de tools con `tools/call`.

### `MCPRegistry`

`MCPRegistry` guarda definiciones MCP ya descubiertas. Es útil para inspección, debugging o para construir una capa de administración más adelante.

### `load_mcp_tools`

`load_mcp_tools` toma la configuración del archivo, registra servidores, descubre tools y las añade al `ToolRegistry` usando `register_external_tool`.

## Archivo de configuración

Yiujarvis busca `mcp_servers.json` en la raíz del proyecto.

Formato recomendado:

```json
{
  "servers": {
    "demo": {
      "command": ["python"],
      "args": ["ruta/al/servidor_mcp.py"],
      "cwd": "C:/ruta/al/proyecto",
      "env": {
        "MI_VARIABLE": "valor"
      },
      "transport": "stdio"
    }
  }
}
```

### Campos

- `command`: comando base del servidor.
- `args`: argumentos extra.
- `cwd`: directorio de trabajo opcional.
- `env`: variables de entorno adicionales.
- `transport`: hoy el proyecto usa `stdio`.

## Cómo crear un servidor MCP local

El servidor tiene que leer líneas JSON-RPC desde `stdin` y responder por `stdout` con una línea JSON por respuesta.

La interfaz mínima que Yiujarvis espera es:

- `initialize`
- `tools/list`
- `tools/call`

### Ejemplo mínimo

```python
import json
import sys

TOOLS = [
    {
        "name": "say_hello",
        "description": "Saluda al usuario",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        },
        "capabilities": ["greeting"],
        "risk": "safe"
    }
]

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        result = {"protocolVersion": "2024-11-05"}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = request.get("params", {})
        arguments = params.get("arguments", {})
        result = {
            "content": [
                {
                    "type": "text",
                    "text": f"Hola {arguments.get('name', 'mundo')}"
                }
            ]
        }
    else:
        result = {}

    print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}), flush=True)
```

## Cómo probarlo en Yiujarvis

1. Crea tu servidor MCP local.
2. Añádelo a `mcp_servers.json`.
3. Ejecuta Yiujarvis.
4. Verás que las tools MCP se registran junto a las locales.

Si el servidor expone una tool con nombre y descripción clara, el ranking y el planner podrán sugerirla como cualquier otra tool.

## Cómo se integra con el planner

El planner no distingue entre tools locales, plugins o MCP si ya están registradas.

Eso significa que puede:

- Planear una acción directa si la intención es obvia.
- Sugerir una tool de MCP si sus capacidades o keywords encajan.
- Ejecutar la tool por el registry sin saber su origen.

## Buenas prácticas

### 1. Define `capabilities`

Las capacidades ayudan al ranking y a futuras reglas de intención.

Ejemplo:

```json
"capabilities": ["music", "audio"]
```

### 2. Escribe `inputSchema` claro

Cuanto más limpio sea el schema, mejor lo entenderá el planner y más fácil será depurarlo.

### 3. Mantén las respuestas pequeñas

Yiujarvis espera una respuesta por línea. Si devuelves bloques muy grandes, el debug se vuelve más difícil.

### 4. Usa `safe` para tools no destructivas

Las tools MCP se registran con riesgo. Si una acción es sensible, colócala como `dangerous` o `sensitive` para que pase por confirmación.

### 5. No dependas de salida multilínea sin formato

El cliente actual prioriza `content` con bloques de `text` o un campo `text` simple.

## Flujo de ejecución interno

Cuando Yiujarvis arranca:

1. Carga tools locales.
2. Carga plugins.
3. Carga servidores MCP si existe `mcp_servers.json`.
4. Descubre tools remotas.
5. Registra todo en el `ToolRegistry`.
6. El planner rankea herramientas locales, plugins y MCP de la misma manera.

## Troubleshooting

### No aparece ninguna tool MCP

Revisa:

- Que `mcp_servers.json` exista.
- Que `command` y `args` sean correctos.
- Que el servidor escriba JSON válido por `stdout`.
- Que la tool aparezca en `tools/list`.

### El servidor se queda colgado

Suele pasar si:

- El servidor no responde una línea por petición.
- Imprime logs por `stdout` en vez de `stderr`.
- Bloquea la lectura de `stdin`.

### `tools/call` devuelve error

Comprueba:

- El nombre exacto de la tool.
- El `arguments` que envía Yiujarvis.
- Que el schema y los parámetros coincidan.

### El servidor no cierra bien

El cliente intenta cerrar el proceso al terminar, pero conviene que el servidor maneje `stdin` cerrado sin dejar procesos huérfanos.

## Estado actual y límites

Lo que ya funciona:

- Descubrimiento local por stdio.
- Registro de tools MCP en el registry general.
- Ejecución por `tools/call`.

Lo que todavía no está implementado:

- Transporte remoto real por red.
- Autenticación avanzada.
- Streaming complejo de resultados MCP.
- Descubrimiento automático de servidores del sistema.

## Recomendación práctica

Si quieres integrar una app concreta, empieza por una tool MCP pequeña y clara, con un schema simple y capacidades bien definidas. Luego añade más acciones, no al revés.

Para este proyecto, la mejor estrategia es:

1. Crear una tool MCP mínima.
2. Ver que aparece en el planner.
3. Probar la ejecución desde consola.
4. Añadir capacidades y más tools.
