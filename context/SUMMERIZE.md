# Resumen del proyecto Yiujarvis

Yiujarvis es un asistente personal por consola para Windows. Su objetivo es conversar con el usuario y ejecutar acciones locales simples, como abrir aplicaciones, listar procesos visibles, cerrar programas y guardar preferencias en una memoria local.

## Objetivo general

El proyecto busca combinar:

- Interacción por terminal con un modelo de IA.
- Herramientas locales para automatizar tareas de Windows.
- Memoria persistente en archivos JSON.
- Detección e indexado de aplicaciones instaladas útiles.

## Flujo principal de ejecución

1. El usuario ejecuta `main.py`.
2. Si hace falta, la app intenta relanzarse como administrador en Windows.
3. Se parsean argumentos de línea de comandos, actualmente solo el proveedor del modelo.
4. Se asegura que el índice de apps exista o se regenere.
5. Se carga la memoria local del usuario.
6. Se inicia el bucle conversacional con el modelo elegido.
7. Si el modelo pide una herramienta, Yiujarvis ejecuta la función local correspondiente y devuelve el resultado al modelo.

## Estructura actual

- `main.py`: punto de entrada, arranque con elevación de permisos y selección de proveedor.
- `src/cli.py`: orquesta el inicio de la aplicación.
- `src/agent.py`: contiene el bucle del asistente, la lista de tools y el despacho de llamadas del modelo.
- `src/tools.py`: funciones locales de utilidad para Windows, clima y memoria.
- `src/app_index.py`: detecta aplicaciones instaladas y mantiene `apps_index.json`.
- `src/config.py`: configura cliente y modelo según el proveedor elegido.
- `src/memory_store.py`: carga y guarda memoria local.
- `memory.json`: persistencia de preferencias y datos útiles del usuario.
- `apps_index.json`: índice de apps útiles detectadas en el sistema.
- `README.md`: documentación de instalación y uso.
- `requirements.txt`: dependencias Python.

## Proveedores de modelo

Actualmente se soportan dos backends:

- `githubmodel`: usa GitHub Models con OpenAI client.
- `groq`: usa Groq y permite salida en streaming.

La selección se hace con `--model` en `main.py`.

## Herramientas locales disponibles

Las tools definidas en `src/tools.py` y registradas en `src/agent.py` son:

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

## Persistencia

Hay dos archivos de estado principales:

- `memory.json`: almacena preferencias del usuario.
- `apps_index.json`: almacena el índice de apps útiles.

Ambos se gestionan localmente y se pueden regenerar si faltan o quedan desactualizados.

## Comportamiento de Windows

El proyecto está pensado específicamente para Windows:

- Usa `ctypes` para intentar elevación de administrador.
- Usa PowerShell para consultar procesos visibles.
- Usa `os.startfile` y `cmd /c start` para abrir apps, URLs y settings.
- Tiene filtros para procesos de sistema que no deberían cerrarse accidentalmente.

## Estado actual del proyecto

La arquitectura es simple y funcional, pero todavía está centrada en herramientas locales fijas. No hay soporte MCP real todavía. Si se quiere conectar con herramientas expuestas por apps instaladas mediante MCP, hace falta agregar una capa adicional de descubrimiento, registro y ejecución de servidores MCP.

## Posibles extensiones futuras

- Integración MCP para apps que expongan tools propias.
- Registro dinámico de herramientas en tiempo de ejecución.
- Allowlist o confirmación antes de ejecutar acciones sensibles.
- Mejor memoria conversacional.
- Mejor índice de software instalado y metadatos por app.

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
