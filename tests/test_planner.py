import unittest

from src.core.tool_registry import Tool, ToolRegistry
from src.planner.planner import Planner
from src.tools import open_app


class PlannerTests(unittest.TestCase):
    def test_music_query_prefers_plugin_tool(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="open_spotify",
                description="Abre Spotify",
                schema={"type": "object", "properties": {}},
                func=lambda: "ok",
                source="plugin",
                keywords=["spotify", "música", "audio"],
                capabilities=["music", "audio"],
                plugin_name="spotify",
            )
        )
        registry.register(
            Tool(
                name="open_app",
                description="Abre una app",
                schema={"type": "object", "properties": {"app": {"type": "string"}}},
                func=open_app,
                keywords=["abrir", "app"],
                capabilities=["app", "system"],
            )
        )

        memory_store = {
            "preferences": {"favorite_music": "spotify"},
            "facts": ["Le gusta la música"],
            "history": [],
        }

        plan = Planner(registry=registry, memory_store=memory_store).build_plan("pon música")

        self.assertEqual(plan.intent, "music")
        self.assertTrue(plan.steps)
        self.assertEqual(plan.steps[0].action, "open_spotify")
        self.assertTrue(any("Memoria relevante" in note for note in plan.notes))

    def test_ask_info_query_suggests_weather(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="get_weather",
                description="Obtiene el clima actual",
                schema={"type": "object", "properties": {}},
                func=lambda: "soleado",
                keywords=["clima", "weather", "temperatura"],
            )
        )

        plan = Planner(registry=registry, memory_store={"preferences": {}, "facts": [], "history": []}).build_plan(
            "qué clima hace"
        )

        self.assertEqual(plan.intent, "ask_info")
        self.assertTrue(plan.steps)
        self.assertEqual(plan.steps[0].action, "get_weather")


if __name__ == "__main__":
    unittest.main()