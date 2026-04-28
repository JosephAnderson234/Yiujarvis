# Yiujarvis

Yiujarvis es un asistente personal por consola para Windows. Conversa con el usuario, planifica acciones, ejecuta tools locales, puede cargar plugins y también descubrir tools MCP mediante servidores locales.

## Funciones

- Conversación por terminal con memoria local.
- Planner y executor separados para ejecutar acciones por pasos.
- Memoria persistente con `preferences`, `facts` e `history`.
- Registro de errores en `erros.log` para depuración posterior.
- Apertura de apps, accesos directos, URLs y utilidades de Windows.
- Confirmación para acciones sensibles y soporte para `dry_run`.
- Ranking de tools por keywords, capacidades e ისტორial.
- Plugins locales con capacidades, incluyendo un plugin de ejemplo para Spotify.
- Base MCP real por stdio/JSON-RPC para tools externas locales.
- Soporte para dos proveedores de IA:
  - `githubmodel`
  - `groq`
- Indexado automático de aplicaciones útiles instaladas en el sistema.
- UI de terminal más visual con banner y colores.
- Tests unitarios para planner, executor, tools, plugins y MCP.

## Requisitos

- Windows
- Python 3.11 o superior
- Una clave de GitHub Models en `GITHUB_TOKEN`
- Opcional: una clave de Groq en `GROQ_API_KEY`

## Pruebas

Ejecuta la batería completa con:

```powershell
python -m unittest discover -s tests
```

## Instalación

1. Crea y activa tu entorno virtual.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instala las dependencias.

```powershell
pip install -r requirements.txt
```

3. Crea un archivo `.env` en la raíz del proyecto con tus credenciales.

```env
GITHUB_TOKEN=tu_token_de_github_models
GROQ_API_KEY=tu_api_key_de_groq
```

4. Si quieres probar MCP, crea `mcp_servers.json` en la raíz con la configuración de tus servidores locales.

```json
{
  "servers": {
    "demo": {
      "command": ["python"],
      "args": ["ruta/al/servidor_mcp.py"]
    }
  }
}
```

## Uso

Ejecuta el asistente desde la raíz del proyecto.

```powershell
python .\main.py
```

Por defecto usa `githubmodel`.

### Elegir proveedor de IA

Usa el parámetro `--model` para cambiar de backend.

```powershell
python .\main.py --model githubmodel
python .\main.py --model groq
```

## Qué puede hacer

- Abrir apps como navegador, terminal, editor, mensajería y utilidades del sistema.
- Revisar procesos activos de Windows y cerrar programas cuando se le solicite.
- Responder preguntas y generar texto usando el modelo elegido.
- Guardar preferencias y hechos útiles del usuario en `memory.json`.
- Cerrar de forma segura y guardar memoria antes de salir.
- Elegir tools por ranking cuando la intención es clara.
- Cargar plugins locales y tools MCP registradas.

## MCP

Si quieres integrar tools externas mediante MCP, revisa [docs/MCP_AVANZADO.md](docs/MCP_AVANZADO.md). Ahí tienes la estructura de `mcp_servers.json`, el ciclo de vida del cliente MCP y un ejemplo de servidor local.

## Archivos generados

Estos archivos se crean o actualizan automáticamente durante el uso:

- `memory.json`: memoria local del asistente.
- `apps_index.json`: índice de apps útiles instaladas.
- `erros.log`: traza persistente de errores.

## Estructura del proyecto

```text
main.py
requirements.txt
.env
erros.log
memory.json
apps_index.json
mcp_servers.json
plugins/
src/
  core/
    agent_loop.py
    tool_registry.py
  intent.py
  memory/
    retrieval.py
  mcp/
    client.py
    loader.py
    registry.py
  planner/
    planner.py
    executor.py
  plugins.py
  app_index.py
  agent.py
  cli.py
  config.py
  error_logger.py
  memory_store.py
  terminal_ui.py
  tools.py
tests/
  test_planner.py
  test_executor.py
  test_tools.py
  test_plugins.py
  test_mcp.py
```

## Notas

- La apertura de apps está pensada para Windows.
- Para cerrar procesos de Windows, ejecuta Yiujarvis como administrador.
- El índice de apps se reconstruye automáticamente si no existe.
- Si usas `groq`, la salida de texto se muestra en streaming.
- La salida de consola usa colores y banner para una lectura más clara.
- Si un plugin falla al cargar, se registra el error y el agente continúa.
- MCP funciona por servidores locales configurados; si no hay `mcp_servers.json`, no se carga nada.
