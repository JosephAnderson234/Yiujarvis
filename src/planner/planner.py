from dataclasses import dataclass, field
from typing import Callable, Optional
import json

from src.app_index import find_best_match, load_apps
from src.intent import classify_intent, extract_targets
from src.tools import SYSTEM_ALIASES, list_running_processes


def _normalize(value):
    return "".join(character for character in value.lower() if character.isalnum())


def _load_running_processes(limit=50):
    payload = list_running_processes(limit=limit)

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]

    processes = []
    for item in data:
        if isinstance(item, dict):
            processes.append(item)

    return processes


def _alias_candidates(target):
    normalized_target = target.lower().strip()
    candidates = {normalized_target, _normalize(normalized_target)}

    mapped = SYSTEM_ALIASES.get(normalized_target)
    if mapped:
        candidates.add(mapped.lower().strip())
        candidates.add(_normalize(mapped))

    for alias, canonical in SYSTEM_ALIASES.items():
        if canonical == normalized_target:
            candidates.add(alias.lower().strip())
            candidates.add(_normalize(alias))

    return {candidate for candidate in candidates if candidate}


def _matches_target(process, target):
    candidate_names = _alias_candidates(target)
    process_name = process.get("name", "")
    window_title = process.get("window_title", "")
    normalized_process_name = _normalize(process_name)
    normalized_window_title = _normalize(window_title)

    if normalized_process_name in candidate_names or normalized_window_title in candidate_names:
        return True

    return any(
        candidate in normalized_process_name or candidate in normalized_window_title
        for candidate in candidate_names
    )


def _is_running(target, running_processes):
    return any(_matches_target(process, target) for process in running_processes)


def _resolve_target(target, apps_available):
    normalized_target = target.lower().strip()

    if normalized_target in apps_available:
        return normalized_target

    mapped = SYSTEM_ALIASES.get(normalized_target)
    if mapped and mapped in apps_available:
        return mapped

    match = find_best_match(normalized_target, apps_available)
    if match:
        return match

    return normalized_target


@dataclass
class Step:
    action: str
    params: dict
    condition: Optional[Callable[[dict], bool]] = None
    condition_name: str = ""
    description: str = ""

    def should_run(self, context):
        if self.condition is None:
            return True

        return bool(self.condition(context))

    def to_dict(self):
        return {
            "action": self.action,
            "params": self.params,
            "condition": self.condition_name,
            "description": self.description,
        }


@dataclass
class Plan:
    steps: list[Step] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    intent: str = "chat"
    notes: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "intent": self.intent,
            "steps": [step.to_dict() for step in self.steps],
            "context": self.context,
            "notes": self.notes,
        }


class Planner:
    def build_plan(self, user_input):
        apps_available = load_apps()
        running_processes = _load_running_processes()

        context = {
            "user_input": user_input,
            "apps_available": sorted(apps_available.keys()),
            "running_processes": running_processes,
            "last_result": None,
        }

        intent = classify_intent(user_input)
        plan = Plan(context=context, intent=intent)

        if intent not in {"open_app", "close_program"}:
            return plan

        targets = extract_targets(user_input)
        if not targets:
            plan.notes.append("No se detectaron acciones concretas.")
            return plan

        for target in targets:
            resolved_target = _resolve_target(target, apps_available)
            is_running_condition = lambda ctx, candidate=resolved_target: _is_running(candidate, ctx.get("running_processes", []))

            if intent == "open_app":
                if _is_running(resolved_target, running_processes):
                    plan.notes.append(f"{resolved_target} ya está abierto.")
                    continue

                if resolved_target not in apps_available and resolved_target not in SYSTEM_ALIASES.values():
                    plan.notes.append(f"No encontré una coincidencia clara para {target}; se intentará abrir igualmente.")

                plan.steps.append(
                    Step(
                        action="open_app",
                        params={"app": resolved_target},
                        condition=lambda ctx, candidate=resolved_target: not _is_running(candidate, ctx.get("running_processes", [])),
                        condition_name="not_already_open",
                        description=f"Abrir {resolved_target}",
                    )
                )
                continue

            if intent == "close_program":
                if not _is_running(resolved_target, running_processes):
                    plan.notes.append(f"{resolved_target} no está abierto.")
                    continue

                plan.steps.append(
                    Step(
                        action="close_program",
                        params={"process_name": resolved_target},
                        condition=is_running_condition,
                        condition_name="already_open",
                        description=f"Cerrar {resolved_target}",
                    )
                )

        return plan