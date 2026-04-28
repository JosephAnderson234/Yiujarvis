# 🧭 VISIÓN DE ESTE PLAN

Al terminar tendrás:

* Un agente que **piensa en pasos (no reacciona)**
* Usa memoria **para decidir, no solo guardar**
* Elige tools **sin depender ciegamente del LLM**
* Puede usar **tools locales y externas indistintamente**

---

# ⚙️ FASE 1 — Planner real (el cambio más importante)

**Duración:** 4–6 días
**Impacto:** 🔥🔥🔥🔥🔥

---

## 🎯 Objetivo

Pasar de:

> “intención → acción directa”

A:

> **“intención → plan estructurado → ejecución”**

---

## 🧩 Qué construir

### 1.1 Estructura de plan

```python
class Plan:
    def __init__(self, steps, context=None):
        self.steps = steps
        self.context = context or {}
```

```python
class Step:
    def __init__(self, action, params, condition=None):
        self.action = action
        self.params = params
        self.condition = condition  # opcional
```

---

### 1.2 Separar responsabilidades

Crea:

```bash
src/planner/
  planner.py
  executor.py
```

---

### 1.3 Planner básico (sin LLM aún)

Ejemplo:

Input:

> "abre vscode y spotify"

Output:

```python
[
  Step("open_app", {"name": "vscode"}),
  Step("open_app", {"name": "spotify"})
]
```

---

### 1.4 Executor

```python
for step in plan.steps:
    if step.condition is None or step.condition():
        tool_registry.execute(step.action, step.params)
```

---

## ✅ Checklist Fase 1

* El agente SIEMPRE genera un plan antes de ejecutar
* Puedes imprimir/debuggear el plan
* El executor está desacoplado

---

# 🧠 FASE 2 — Planner inteligente (condiciones + validación)

**Duración:** 4–5 días
**Impacto:** 🔥🔥🔥🔥

---

## 🎯 Objetivo

Que el agente no solo ejecute, sino que **razone antes de actuar**

---

## 🧩 Qué añadir

### 2.1 Condiciones en pasos

```python
Step(
  action="open_app",
  params={"name": "vscode"},
  condition=lambda ctx: not ctx["is_open"]
)
```

---

### 2.2 Pre-checks

Antes de ejecutar:

* ¿la app existe?
* ¿ya está abierta?

---

### 2.3 Contexto compartido

```python
plan.context = {
  "apps_available": [...],
  "running_processes": [...]
}
```

---

### 2.4 Resultado por step

```python
result = executor.run(step)
plan.context["last_result"] = result
```

---

## ✅ Checklist Fase 2

* El agente evita acciones redundantes
* Puede tomar decisiones durante ejecución
* Usa contexto real del sistema

---

# 🧠 FASE 3 — Memory Retrieval Layer

**Duración:** 3–4 días
**Impacto:** 🔥🔥🔥🔥

---

## 🎯 Objetivo

Que la memoria influya decisiones

---

## 🧩 Qué construir

### 3.1 Módulo nuevo

```bash
src/memory/
  retrieval.py
```

---

### 3.2 Función central

```python
def get_relevant_memory(query: str, memory_store) -> list:
    ...
```

---

### 3.3 Integración

Antes de planear:

```python
memory_context = get_relevant_memory(user_input)
```

Y lo pasas a:

* planner
* LLM (si aplica)

---

### 3.4 Scoring simple

* keywords
* coincidencias parciales
* prioridad a “preferences”

---

## 🔥 Opcional (pero top)

* embeddings locales

---

## ✅ Checklist Fase 3

* El agente recuerda cosas útiles automáticamente
* La memoria afecta el plan generado

---

# 🔌 FASE 4 — Tool Intelligence (ranking + selección)

**Duración:** 3–5 días
**Impacto:** 🔥🔥🔥

---

## 🎯 Objetivo

Reducir dependencia del LLM para elegir tools

---

## 🧩 Qué hacer

### 4.1 Enriquecer tools

```python
Tool(
  name="open_app",
  description="abre aplicaciones",
  keywords=["abrir", "programa", "app"]
)
```

---

### 4.2 Ranking

```python
def rank_tools(query, tools):
    ...
```

Criterios:

* keywords
* similitud texto
* uso histórico

---

### 4.3 Integración en planner

Antes de decidir:

```python
best_tools = rank_tools(user_input)
```

---

## ✅ Checklist Fase 4

* El sistema sugiere tools sin LLM
* Mejora precisión en acciones

---

# 🔌 FASE 5 — Plugins con capacidades

**Duración:** 3–4 días
**Impacto:** 🔥🔥🔥

---

## 🎯 Objetivo

Que el agente entienda “qué sabe hacer cada plugin”

---

## 🧩 Qué hacer

### 5.1 Definir capacidades

```python
{
  "plugin": "spotify",
  "capabilities": ["music", "audio"]
}
```

---

### 5.2 Asociar tools a capacidades

---

### 5.3 Matching por intención

```python
if intent == "music":
    usar plugin spotify
```

---

## ✅ Checklist Fase 5

* El agente elige plugins inteligentemente
* No depende solo del nombre de la tool

---

# 🌐 FASE 6 — MCP real (primer integración)

**Duración:** 5–7 días
**Impacto:** 🔥🔥🔥🔥🔥

---

## 🎯 Objetivo

Convertir tu sistema en extensible de verdad

---

## 🧩 Qué hacer

### 6.1 Levantar servidor MCP simple

Aunque sea local con 2 tools.

---

### 6.2 Cliente MCP funcional

En `src/mcp/client.py`:

* conectar
* listar tools
* ejecutar tool

---

### 6.3 Registrar tools MCP en tu registry

👉 Igual que las locales

---

### 6.4 Transparencia total

El planner NO debe saber si:

* tool es local
* tool es remota

---

## ✅ Checklist Fase 6

* Puedes ejecutar una tool externa real
* No hay diferencia en ejecución

---

# 🧪 FASE 7 — Testing del sistema inteligente

**Duración:** 3–4 días
**Impacto:** 🔥🔥🔥

---

## 🎯 Objetivo

Evitar que todo se rompa

---

## 🧩 Qué testear

### 7.1 Planner

```python
input → expected plan
```

---

### 7.2 Executor

* steps correctos
* manejo de errores

---

### 7.3 Tools

* mocks de sistema

---

## ✅ Checklist Fase 7

* Puedes refactorizar sin miedo
* Detectas errores rápido

---

# 🚀 ORDEN RECOMENDADO (CRÍTICO)

No lo hagas en paralelo:

1. Fase 1 → Planner base
2. Fase 2 → Planner inteligente
3. Fase 3 → Memory retrieval
4. Fase 4 → Tool ranking
5. Fase 6 → MCP real 🔥
6. Fase 5 → Plugins con capacidades
7. Fase 7 → Testing

---

# 💬 CONCLUSIÓN DIRECTA

Ahora mismo tu sistema es:

👉 **reactivo e inteligente a medias**

Con este plan pasa a:

👉 **agente deliberativo (piensa antes de actuar)**
