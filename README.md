# Yiujarvis

Yiujarvis es un asistente personal por consola para Windows que usa modelos de IA para conversar y ejecutar herramientas como abrir aplicaciones, consultar clima y guardar preferencias del usuario.

## Funciones

- Conversación por terminal con memoria local.
- Apertura de apps, accesos directos, URLs y utilidades de Windows.
- Soporte para dos proveedores de IA:
  - `githubmodel`
  - `groq`
- Indexado automático de aplicaciones útiles instaladas en el sistema.
- Persistencia local de memoria y del índice de apps.

## Requisitos

- Windows
- Python 3.11 o superior
- Una clave de GitHub Models en `GITHUB_TOKEN`
- Opcional: una clave de Groq en `GROQ_API_KEY`

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
- Responder preguntas y generar texto usando el modelo elegido.
- Guardar preferencias del usuario en `memory.json`.

## Archivos generados

Estos archivos se crean o actualizan automáticamente durante el uso:

- `memory.json`: memoria local del asistente.
- `apps_index.json`: índice de apps útiles instaladas.

## Estructura del proyecto

```text
main.py
requirements.txt
.env
src/
  app_index.py
  agent.py
  cli.py
  config.py
  memory_store.py
  tools.py
```

## Notas

- La apertura de apps está pensada para Windows.
- El índice de apps se reconstruye automáticamente si no existe.
- Si usas `groq`, la salida de texto se muestra en streaming.
