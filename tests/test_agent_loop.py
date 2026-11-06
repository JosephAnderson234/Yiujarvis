import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from src.core.agent_loop import compact_conversation, run_agent_turn
from src.core.tool_registry import Tool, ToolRegistry


def _chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tool_call_delta(index, call_id=None, name=None, arguments=None):
    return SimpleNamespace(
        index=index,
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def _registry_with(name, func):
    registry = ToolRegistry()
    registry.register(
        Tool(
            name=name,
            description=name,
            schema={"type": "object", "properties": {"city": {"type": "string"}}},
            func=func,
        )
    )
    return registry


class RunAgentTurnTests(unittest.TestCase):
    def test_sensitive_tool_is_denied_without_approval_handler(self):
        calls = []
        registry = ToolRegistry()
        registry.register(Tool("danger", "danger", {"type": "object"}, lambda: calls.append(True), risk="dangerous"))

        self.assertEqual(registry.execute("danger"), "Ejecución cancelada para danger")
        self.assertEqual(calls, [])

    def test_chains_tool_calls_until_final_answer(self):
        calls = []

        def get_weather(city=""):
            calls.append(city)
            return f"{city}: 20°C"

        responses = [
            # Ronda 1: argumentos llegan fragmentados en varios chunks.
            iter(
                [
                    _chunk(tool_calls=[_tool_call_delta(0, "call_a", "get_weather", '{"ci')]),
                    _chunk(tool_calls=[_tool_call_delta(0, None, None, 'ty": "Lima"}')]),
                ]
            ),
            # Ronda 2: el modelo decide consultar otra ciudad tras ver el primer resultado.
            iter([_chunk(tool_calls=[_tool_call_delta(0, "call_b", "get_weather", '{"city": "Cusco"}')])]),
            # Ronda 3: respuesta final en streaming.
            iter([_chunk(content="Lima 20°C, "), _chunk(content="Cusco 20°C.")]),
        ]
        client = FakeClient(responses)
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "clima lima y cusco"}]

        with redirect_stdout(io.StringIO()):
            answer = run_agent_turn(client, "model", messages, _registry_with("get_weather", get_weather))

        self.assertEqual(answer, "Lima 20°C, Cusco 20°C.")
        self.assertEqual(calls, ["Lima", "Cusco"])
        self.assertEqual(
            [message["role"] for message in messages],
            ["system", "user", "assistant", "tool", "assistant", "tool", "assistant"],
        )
        self.assertEqual(messages[3]["tool_call_id"], "call_a")
        self.assertEqual(messages[3]["content"], "Lima: 20°C")
        self.assertTrue(all("tools" in request for request in client.chat.completions.requests))

    def test_invalid_json_arguments_are_reported_back_to_model(self):
        responses = [
            iter([_chunk(tool_calls=[_tool_call_delta(0, "call_a", "get_weather", "{roto")])]),
            iter([_chunk(content="Perdón, reintento luego.")]),
        ]
        client = FakeClient(responses)
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "clima"}]

        with redirect_stdout(io.StringIO()):
            run_agent_turn(client, "model", messages, _registry_with("get_weather", lambda city="": "x"))

        self.assertIn("Argumentos inválidos", messages[3]["content"])

    def test_stops_after_max_rounds_and_forces_answer(self):
        from src.core import agent_loop

        looping = [
            iter([_chunk(tool_calls=[_tool_call_delta(0, f"call_{i}", "get_weather", "{}")])])
            for i in range(agent_loop.MAX_TOOL_ROUNDS)
        ]
        client = FakeClient([*looping, iter([_chunk(content="Listo.")])])
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "x"}]

        with redirect_stdout(io.StringIO()):
            answer = run_agent_turn(client, "model", messages, _registry_with("get_weather", lambda city="": "x"))

        self.assertEqual(answer, "Listo.")
        self.assertEqual(client.chat.completions.requests[-1]["tool_choice"], "none")


    def test_empty_stream_raises_instead_of_staying_silent(self):
        client = FakeClient([iter([])])
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "x"}]

        with redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            run_agent_turn(client, "model", messages, _registry_with("get_weather", lambda city="": "x"))


class CompactConversationTests(unittest.TestCase):
    def test_keeps_recent_turns_and_never_starts_on_tool_message(self):
        from src.core import agent_loop

        messages: list[dict] = [{"role": "system", "content": "sys"}]
        for index in range(agent_loop.MAX_CONTEXT_MESSAGES):
            messages.append({"role": "user", "content": f"u{index}"})
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": f"c{index}", "type": "function", "function": {"name": "t", "arguments": "{}"}}],
                }
            )
            messages.append({"role": "tool", "tool_call_id": f"c{index}", "content": "ok"})

        summary_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="- resumen"))]
        )
        client = FakeClient([summary_response])

        summary = compact_conversation(client, "model", messages, "")

        self.assertEqual(summary, "- resumen")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertLessEqual(len(messages) - 1, agent_loop.KEEP_RECENT_MESSAGES)

    def test_short_conversation_is_untouched(self):
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hola"}]
        client = FakeClient([])

        self.assertEqual(compact_conversation(client, "model", messages, "previo"), "previo")
        self.assertEqual(len(messages), 2)


if __name__ == "__main__":
    unittest.main()
