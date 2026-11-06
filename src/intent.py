import re


OPEN_KEYWORDS = ("abre", "abrir", "open", "launch", "inicia", "iniciar", "ejecuta", "lanza")
CLOSE_KEYWORDS = ("cierra", "cerrar", "close", "termina", "terminar", "mata")
SAVE_KEYWORDS = ("guarda", "guardar", "recuerda", "remember", "anota")
SHUTDOWN_KEYWORDS = ("apágate", "apagate", "apagarte", "apagar", "apagarse", "salte", "salir", "exit", "quit", "adiós", "adios")
QUESTION_KEYWORDS = ("qué", "que", "como", "cómo", "por qué", "porque", "cuál", "cual", "cuándo", "cuando", "dónde", "donde", "who", "what", "when", "where", "why", "how")
MUSIC_KEYWORDS = ("música", "musica", "music", "spotify", "audio", "canción", "canciones", "song", "songs", "play")
SEPARATORS = (" y luego ", " despues ", " después ", " then ", ",", " y ")
WAKE_PREFIX = r"^(?:(?:hey|oye)\s+)?(?:yiujarvis|jarvis)?[\s,:]*(?:por\s+favor\s+)?"
DIRECT_COMMAND_MAX_WORDS = 8


def _keyword_pattern(keywords):
    alternatives = "|".join(re.escape(keyword) for keyword in sorted(keywords, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")


OPEN_PATTERN = _keyword_pattern(OPEN_KEYWORDS)
CLOSE_PATTERN = _keyword_pattern(CLOSE_KEYWORDS)
SAVE_PATTERN = _keyword_pattern(SAVE_KEYWORDS)
QUESTION_PATTERN = _keyword_pattern(QUESTION_KEYWORDS)
MUSIC_PATTERN = _keyword_pattern(MUSIC_KEYWORDS)
COMMAND_KEYWORDS_PATTERN = _keyword_pattern(OPEN_KEYWORDS + CLOSE_KEYWORDS + SAVE_KEYWORDS)


def _strip_wake_prefix(normalized):
    return re.sub(WAKE_PREFIX, "", normalized).strip()


def is_shutdown_command(text):
    normalized = re.sub(r"[^\w\s]+", " ", text.lower()).strip()
    normalized = _strip_wake_prefix(normalized)
    normalized = re.sub(r"\s+por\s+favor$", "", normalized).strip()
    return normalized in SHUTDOWN_KEYWORDS


def classify_intent(text):
    normalized = text.lower().strip()

    if is_shutdown_command(normalized):
        return "shutdown"

    if OPEN_PATTERN.search(normalized):
        return "open_app"

    if CLOSE_PATTERN.search(normalized):
        return "close_program"

    if SAVE_PATTERN.search(normalized):
        return "save_preference"

    if MUSIC_PATTERN.search(normalized) and not normalized.endswith("?"):
        return "music"

    if normalized.endswith("?") or QUESTION_PATTERN.search(normalized):
        return "ask_info"

    return "chat"


def is_direct_command(text):
    """True cuando el mensaje es una orden corta tipo "abre X y Y" que no necesita al LLM."""
    normalized = _strip_wake_prefix(text.lower().strip())

    if not normalized or normalized.endswith("?"):
        return False

    if len(normalized.split()) > DIRECT_COMMAND_MAX_WORDS:
        return False

    first_word = normalized.split()[0]
    return first_word in OPEN_KEYWORDS or first_word in CLOSE_KEYWORDS


def extract_targets(text):
    normalized = _strip_wake_prefix(text.lower().strip())
    cleaned = COMMAND_KEYWORDS_PATTERN.sub("", normalized)

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
