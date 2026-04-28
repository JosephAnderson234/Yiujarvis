import re


def _tokenize(query):
    return {
        token
        for token in re.findall(r"[a-záéíóúñü0-9]+", query.lower())
        if len(token) > 2
    }


def _count_history_usage(query, history, tool_name):
    if not isinstance(history, list):
        return 0

    usage = 0
    needle = tool_name.lower()

    for item in history[-40:]:
        if not isinstance(item, dict):
            continue

        content = str(item.get("content", "")).lower()
        if needle in content:
            usage += 1

    return usage


def _capabilities_for_tool(tool):
    return {
        capability.lower()
        for capability in getattr(tool, "capabilities", []) or []
        if capability
    }


def rank_tools(query, tools, history=None, desired_capabilities=None):
    query_tokens = _tokenize(query)
    desired_capabilities = {
        capability.lower()
        for capability in (desired_capabilities or [])
        if capability
    }
    ranked = []

    for tool in tools:
        keywords = {keyword.lower() for keyword in getattr(tool, "keywords", []) if keyword}
        capabilities = _capabilities_for_tool(tool)
        description = getattr(tool, "description", "") or ""
        name = getattr(tool, "name", "") or ""
        combined_text = f"{name} {description} {' '.join(keywords)}".lower()

        score = 0.0
        reasons = []

        for token in query_tokens:
            if token in combined_text:
                score += 1.6
                reasons.append(f"match:{token}")

        for keyword in keywords:
            if keyword in query.lower():
                score += 2.0
                reasons.append(f"keyword:{keyword}")

        if name and name.lower() in query.lower():
            score += 3.0
            reasons.append(f"name:{name}")

        capability_overlap = capabilities & desired_capabilities
        if capability_overlap:
            score += 3.5 + (0.5 * len(capability_overlap))
            reasons.append(f"capability:{','.join(sorted(capability_overlap))}")

        for capability in capabilities:
            if capability in query.lower() or capability in combined_text:
                score += 1.0
                reasons.append(f"toolcap:{capability}")

        usage_bonus = _count_history_usage(query, history or [], name)
        if usage_bonus:
            score += min(usage_bonus * 0.3, 1.5)
            reasons.append(f"history:{usage_bonus}")

        if getattr(tool, "source", "local") != "local":
            score += 0.1

        ranked.append(
            {
                "tool": tool,
                "score": round(score, 2),
                "reasons": reasons,
                "capabilities": sorted(capabilities),
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def select_best_tool(query, tools, history=None, desired_capabilities=None, threshold=2.6):
    ranked = rank_tools(query, tools, history=history, desired_capabilities=desired_capabilities)
    if not ranked:
        return None, ranked

    best = ranked[0]
    if best["score"] < threshold:
        return None, ranked

    return best, ranked
