import unittest

from src.core.tool_registry import Tool, ToolRegistry
from src.planner.executor import PlanExecutor
from src.planner.planner import Plan, Step


class ExecutorTests(unittest.TestCase):
    def test_executor_updates_context_and_skips_false_conditions(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="say_hi",
                description="saluda",
                schema={"type": "object", "properties": {}},
                func=lambda: "hi",
            )
        )

        plan = Plan(
            steps=[
                Step(action="say_hi", params={}, condition=lambda ctx: True, condition_name="run"),
                Step(action="say_hi", params={}, condition=lambda ctx: False, condition_name="skip"),
            ],
            context={"running_processes": []},
            intent="chat",
        )

        results = PlanExecutor(registry).run(plan)

        self.assertEqual(results[0], "hi")
        self.assertIn("[skipped] say_hi", results[1])
        self.assertEqual(plan.context["last_result"], "hi")
        self.assertEqual(len(plan.context["step_results"]), 2)


if __name__ == "__main__":
    unittest.main()