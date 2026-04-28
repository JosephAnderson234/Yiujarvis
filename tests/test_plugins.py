import unittest

from src.core.agent_loop import build_tool_registry


class PluginTests(unittest.TestCase):
    def test_spotify_plugin_is_loaded_with_capabilities(self):
        registry = build_tool_registry()
        tool = registry.get("open_spotify")

        self.assertIsNotNone(tool)
        self.assertIn("music", tool.capabilities)
        self.assertEqual(tool.source, "plugin")


if __name__ == "__main__":
    unittest.main()