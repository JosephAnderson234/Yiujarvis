# Resumen del proyecto Yiujarvis

Yiujarvis es un asistente personal por consola para Windows. Hoy ya no es solo un loop de chat: incorpora planificación por pasos, memoria útil, ranking de tools, plugins con capacidades, soporte MCP real y tests unitarios.

## Objetivo general

El proyecto combina:

- Interacción por terminal con un modelo de IA.
- Automatización local de Windows.
- Memoria persistente en JSON.
- Registro de errores en archivo para depuración.
- Descubrimiento de apps instaladas.
- Extensibilidad por plugins y base MCP.
- Planner deliberativo con executor separado.
- Ranking de tools por keywords, capacidades e historial.
- UI de terminal más visual.
- Pruebas unitarias del sistema inteligente.

## Estado actual por fases

### Fase 1 y 2

La base ya está estabilizada:

- El loop principal vive en [src/core/agent_loop.py](src/core/agent_loop.py).
- Las tools están registradas con un `ToolRegistry` tipado en [src/core/tool_registry.py](src/core/tool_registry.py).
- La memoria usa el esquema `preferences`, `facts` y `history` en [src/memory_store.py](src/memory_store.py).
- Se mantiene memoria corta en runtime con `deque`.
- El planner se separó en [src/planner/planner.py](src/planner/planner.py) y [src/planner/executor.py](src/planner/executor.py).

### Fase 3

Ya hay seguridad básica:

- Tools sensibles requieren confirmación.
- `close_program` bloquea procesos críticos.
- Existe soporte para `dry_run`.
- Los errores se registran en [erros.log](erros.log).
- El apagado del asistente guarda la memoria antes de salir.

### Fase 4

La extensibilidad ya funciona:

- Carga automática de plugins locales con [src/plugins.py](src/plugins.py).
- Los plugins pueden declarar capacidades y el ranking las usa.
- Existe un plugin de ejemplo en [plugins/spotify/plugin.py](plugins/spotify/plugin.py).
- MCP funciona por stdio/JSON-RPC con [src/mcp/client.py](src/mcp/client.py), [src/mcp/loader.py](src/mcp/loader.py) y [src/mcp/registry.py](src/mcp/registry.py).
- La carga MCP se basa en `mcp_servers.json` si existe.

### Fase 5 y 6

El agente ya entiende mejor la intención y la terminal mejoró visualmente:

- Detecta acciones simples con [src/intent.py](src/intent.py).
- Planifica órdenes compuestas como abrir varias apps.
- Tiene una UI más clara en [src/terminal_ui.py](src/terminal_ui.py).
- Muestra banner, proveedor activo y cantidad de tools al iniciar.
- El prompt del modelo incluye memoria relevante y tools mejor rankeadas.

### Fase 7

La base está testeada con `unittest`:

- Planner.
- Executor.
- Tools.
- Plugins.
- MCP local de prueba.

## Flujo principal de ejecución

1. El usuario ejecuta `main.py`.
2. Si hace falta, la app intenta relanzarse como administrador en Windows.
3. Se parsea el proveedor del modelo.
4. Se asegura que el índice de apps exista o se regenere.
5. Se carga la memoria local.
6. `src/cli.py` muestra el banner y el estado inicial.
7. `src/core/agent_loop.py` arranca el bucle conversacional.
8. El planner construye un plan con contexto de memoria y ranking de tools.
9. Si la intención es simple, el executor puede ejecutar pasos directos sin pasar por el LLM.
10. Si el modelo pide tools, se despachan desde el registry.
11. Cada salida relevante persiste memoria y errores si corresponde.

## Estructura actual

- `main.py`: punto de entrada, elevación de permisos y selección de proveedor.
- `src/cli.py`: arranque general y presentación visual inicial.
- `src/agent.py`: wrapper del loop principal.
- `src/core/agent_loop.py`: conversación, planning, tool calls, persistencia y apagado.
- `src/core/tool_registry.py`: registro y ejecución segura de tools.
- `src/tools.py`: tools locales de Windows, clima y memoria.
- `src/intent.py`: clasificación de intención y extracción de objetivos.
- `src/terminal_ui.py`: banner, colores y mensajes visuales de consola.
- `src/plugins.py`: carga de plugins locales.
- `src/mcp/`: cliente, loader y registry MCP.
- `src/planner/`: planner y executor.
- `src/memory/`: retrieval de memoria relevante.
- `src/tool_ranking.py`: ranking de tools.
- `src/app_index.py`: detecta aplicaciones instaladas y mantiene `apps_index.json`.
- `src/config.py`: configura cliente y modelo según el proveedor.
- `src/memory_store.py`: carga, normaliza y guarda memoria local.
- `src/error_logger.py`: configuración del log persistente.
- `memory.json`: persistencia de preferencias, hechos y historial.
- `apps_index.json`: índice de apps útiles detectadas en el sistema.
- `erros.log`: archivo de errores para depuración.
- `mcp_servers.json`: configuración opcional de servidores MCP locales.
- `plugins/spotify/plugin.py`: plugin de ejemplo con capacidades `music` y `audio`.
- `context/SUMMERIZE.md`: resumen del proyecto.
- `README.md`: documentación de instalación y uso.
- `requirements.txt`: dependencias Python.
- `tests/`: batería de pruebas unitarias.

## Proveedores de modelo

Actualmente se soportan dos backends:

- `githubmodel`: usa GitHub Models con cliente OpenAI.
- `groq`: usa Groq y permite salida en streaming.

La selección se hace con `--model` en `main.py`.

## Herramientas locales disponibles

Las tools actuales incluyen:

- `get_weather`: devuelve un clima de ejemplo.
- `open_app`: abre apps instaladas, URLs o utilidades del sistema.
- `list_running_processes`: lista ventanas visibles y procesos asociados.
- `close_program`: cierra un proceso abierto por nombre o ventana.
- `save_user_preference`: guarda pares clave-valor en memoria.

## Lógica de apps instaladas

El proyecto no usa una base de datos de software instalada completa. En cambio:

- Recorre rutas típicas de Windows como Program Files, Start Menu y AppData.
- Filtra ejecutables y accesos directos relevantes.
- Guarda solo apps consideradas útiles.
- Busca coincidencias aproximadas para abrir aplicaciones por nombre.
- `open_app` ya usa `os.startfile` o `start` de Windows para manejar mejor accesos directos `.lnk`.

## Persistencia

Hay varios archivos de estado principales:

- `memory.json`: almacena preferencias, hechos e historial.
- `apps_index.json`: almacena el índice de apps útiles.
- `erros.log`: guarda trazas de error para depurar después.

Todos son locales y se regeneran o reutilizan según haga falta.

## Comportamiento de Windows

El proyecto está pensado específicamente para Windows:

- Usa `ctypes` para intentar elevación de administrador.
- Usa PowerShell para consultar procesos visibles.
- Usa `os.startfile` y `cmd /c start` para abrir apps, URLs y settings.
- Tiene filtros para procesos de sistema que no deberían cerrarse accidentalmente.
- Puede apagarse de forma controlada guardando memoria antes de salir.

## Estado actual del proyecto

- La arquitectura ya está bastante modular y funcional:

- Hay separación clara entre loop, tools, intención, UI y persistencia.
- El agente puede resolver órdenes simples sin depender siempre del LLM.
- Las acciones sensibles están protegidas por confirmación.
- Existe base para plugins locales y MCP, y ya hay integración MCP funcional por servidores locales.
- El proyecto está cubierto por tests de planner, executor, tools, plugins y MCP.

## Posibles extensiones futuras

- Integración MCP real para apps que expongan tools propias.
- Registro dinámico de más herramientas de servidores externos.
- Allowlist por plugin o por tool.
- Memoria semántica más rica.
- Mejor empaquetado de terminal o interfaz web.

## Ejecución

Arranque típico:

```powershell
python .\main.py
```

Elegir proveedor:

```powershell
python .\main.py --model githubmodel
python .\main.py --model groq
```
