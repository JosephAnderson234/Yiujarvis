import json
import os
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.cli_model import CLIAgentClient, _cli_environment, _run_cli
from src.config import get_model_config
from src.core.agent_loop import run_agent_turn
from src.core.tool_registry import Tool, ToolRegistry


TOOLS = [{"type": "function", "function": {
    "name": "get_weather", "description": "Clima", "parameters": {"type": "object"}
}}]


class CLIModelTests(unittest.TestCase):
    def test_provider_needs_no_api_key_and_keeps_tool_loop_shape(self):
        config = get_model_config("codex")
        self.assertEqual(config["provider"], "codex")
        client = CLIAgentClient("codex")
        payload = {"content": "", "tool_calls": [{"name": "get_weather", "arguments": '{"city":"Lima"}'}]}
        with patch("src.cli_model._run_cli", return_value=payload):
            chunk = next(client.chat.completions.create(
                model="codex-cli", messages=[{"role": "user", "content": "clima"}],
                tools=TOOLS, stream=True,
            ))
        call = chunk.choices[0].delta.tool_calls[0]
        self.assertEqual(call.function.name, "get_weather")
        self.assertEqual(json.loads(call.function.arguments), {"city": "Lima"})

    def test_unknown_tool_is_rejected(self):
        client = CLIAgentClient("claude")
        payload = {"content": "", "tool_calls": [{"name": "PowerShell", "arguments": "{}"}]}
        with patch("src.cli_model._run_cli", return_value=payload), self.assertRaises(RuntimeError):
            client.chat.completions.create(model="claude-cli", messages=[], tools=TOOLS)

    def test_cli_tool_call_is_executed_by_yiujarvis_registry(self):
        registry = ToolRegistry()
        registry.register(Tool(
            "get_weather", "Clima", {"type": "object"}, lambda city: f"{city}: 20 C"
        ))
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "clima Lima"}]
        responses = [
            {"content": "", "tool_calls": [{"name": "get_weather", "arguments": '{"city":"Lima"}'}]},
            {"content": "En Lima hay 20 C.", "tool_calls": []},
        ]
        with patch("src.cli_model._run_cli", side_effect=responses) as cli, redirect_stdout(io.StringIO()):
            answer = run_agent_turn(CLIAgentClient("codex"), "codex-cli", messages, registry)
        self.assertEqual(answer, "En Lima hay 20 C.")
        self.assertEqual(messages[3]["content"], "Lima: 20 C")
        self.assertIn("Lima: 20 C", cli.call_args_list[1].args[1])

    def test_codex_uses_read_only_temp_directory_and_schema(self):
        def fake_run(command, **kwargs):
            self.assertIn("--sandbox", command)
            self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
            self.assertIn("--ignore-user-config", command)
            self.assertIn("--ephemeral", command)
            self.assertEqual(kwargs["cwd"], command[command.index("--cd") + 1])
            Path(command[command.index("--output-last-message") + 1]).write_text(
                '{"content":"Hola","tool_calls":[]}', encoding="utf-8"
            )
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch("src.cli_model.shutil.which", return_value="codex.exe"), patch(
            "src.cli_model.subprocess.run", side_effect=fake_run
        ):
            self.assertEqual(_run_cli("codex", "hola")["content"], "Hola")

    def test_claude_uses_subscription_login_and_no_builtin_tools(self):
        result = SimpleNamespace(returncode=0, stdout=json.dumps({
            "structured_output": {"content": "Hola", "tool_calls": []}
        }), stderr="")
        with patch("src.cli_model.shutil.which", return_value="claude.exe"), patch(
            "src.cli_model.subprocess.run", return_value=result
        ) as run:
            self.assertEqual(_run_cli("claude", "hola")["content"], "Hola")
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--safe-mode", args)
        self.assertNotIn("ANTHROPIC_API_KEY", run.call_args.kwargs["env"])

    def test_cli_environment_excludes_api_keys(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "secret", "OPENAI_API_KEY": "secret", "PATH": "bin"}):
            environment = _cli_environment()
        self.assertEqual(environment["PATH"], "bin")
        self.assertNotIn("ANTHROPIC_API_KEY", environment)
        self.assertNotIn("OPENAI_API_KEY", environment)


if __name__ == "__main__":
    unittest.main()
