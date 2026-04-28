import re


OPEN_KEYWORDS = ("abre", "abrir", "open", "launch", "inicia", "iniciar")
CLOSE_KEYWORDS = ("cierra", "cerrar", "close", "termina", "terminar", "mata")
SAVE_KEYWORDS = ("guarda", "guardar", "recuerda", "remember", "anota")
SHUTDOWN_KEYWORDS = ("apágate", "apagate", "apagarte", "apagar", "apagarse", "salte", "salir", "exit", "quit")
QUESTION_KEYWORDS = ("qué", "como", "cómo", "por qué", "porque", "who", "what", "when", "where", "why", "how")
MUSIC_KEYWORDS = ("música", "musica", "music", "spotify", "audio", "canción", "canciones", "song", "songs", "play")
SEPARATORS = (" y luego ", " despues ", " después ", " then ", ",", " y ")


def classify_intent(text):
    normalized = text.lower().strip()

    if any(keyword in normalized for keyword in OPEN_KEYWORDS):
        return "open_app"

    if any(keyword in normalized for keyword in CLOSE_KEYWORDS):
        return "close_program"

    if any(keyword in normalized for keyword in SAVE_KEYWORDS):
        return "save_preference"

    if any(keyword in normalized for keyword in SHUTDOWN_KEYWORDS):
        return "shutdown"

    if any(keyword in normalized for keyword in MUSIC_KEYWORDS):
        return "music"

    if normalized.startswith("que ") or normalized.startswith("qué "):
        return "ask_info"

    if normalized.endswith("?") or any(keyword in normalized for keyword in QUESTION_KEYWORDS):
        return "ask_info"

    return "chat"


def extract_targets(text):
    normalized = text.lower().strip()
    cleaned = normalized

    for prefix in OPEN_KEYWORDS + CLOSE_KEYWORDS + SAVE_KEYWORDS:
        cleaned = cleaned.replace(prefix, "")

    parts = [cleaned]
    for separator in SEPARATORS:
        next_parts = []
        for part in parts:
            next_parts.extend(part.split(separator))
        parts = next_parts

    targets = []
    for part in parts:
        candidate = re.sub(r"\b(luego|despues|después|and|then|por favor|favor)\b", "", part).strip()
        candidate = re.sub(r"[^\w\-\. ]+", " ", candidate).strip()
        if candidate:
            targets.append(candidate)

    return targets


def build_action_plan(text):
    intent = classify_intent(text)
    targets = extract_targets(text)

    if intent not in {"open_app", "close_program"} or not targets:
        return {"intent": intent, "steps": []}

    tool_name = "open_app" if intent == "open_app" else "close_program"
    steps = []

    for target in targets:
        steps.append({"tool": tool_name, "arguments": {"app" if tool_name == "open_app" else "process_name": target}})

    return {"intent": intent, "steps": steps}