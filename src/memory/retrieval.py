import re


def _tokenize(query):
    return {
        token
        for token in re.findall(r"[a-záéíóúñü0-9]+", query.lower())
        if len(token) > 2
    }


def _score_text(query_tokens, text, base_score=0):
    if not text:
        return base_score

    normalized_text = str(text).lower()
    score = base_score

    for token in query_tokens:
        if token in normalized_text:
            score += 2

    return score


def get_relevant_memory(query: str, memory_store, limit: int = 5) -> list:
    query_tokens = _tokenize(query)
    memory_store = memory_store if isinstance(memory_store, dict) else {}
    preferences = memory_store.get("preferences", {}) if isinstance(memory_store.get("preferences"), dict) else {}
    facts = memory_store.get("facts", []) if isinstance(memory_store.get("facts"), list) else []
    history = memory_store.get("history", []) if isinstance(memory_store.get("history"), list) else []

    matches = []

    for key, value in preferences.items():
        score = _score_text(query_tokens, key, base_score=4)
        score = _score_text(query_tokens, value, base_score=score)

        if score > 4:
            matches.append(
                {
                    "source": "preferences",
                    "key": key,
                    "value": value,
                    "score": score,
                }
            )

    for fact in facts:
        score = _score_text(query_tokens, fact, base_score=1)
        if score > 1:
            matches.append(
                {
                    "source": "facts",
                    "value": fact,
                    "score": score,
                }
            )

    for item in history[-20:]:
        if not isinstance(item, dict):
            continue

        content = item.get("content", "")
        role = item.get("role", "")
        score = _score_text(query_tokens, content, base_score=0)

        if score > 0:
            matches.append(
                {
                    "source": f"history:{role}",
                    "value": content,
                    "score": score,
                }
            )

    matches.sort(key=lambda item: item.get("score", 0), reverse=True)
    return matches[: max(1, limit)]
