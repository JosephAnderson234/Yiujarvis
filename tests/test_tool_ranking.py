import unittest
from dataclasses import dataclass, field

from src.tool_ranking import rank_tools, select_best_tool


@dataclass
class FakeTool:
    name: str
    description: str = ""
    keywords: list = field(default_factory=list)
    capabilities: list = field(default_factory=list)
    source: str = "local"


class RankToolsTests(unittest.TestCase):
    def setUp(self):
        self.open_app = FakeTool(
            name="open_app",
            description="Abre una aplicacion",
            keywords=["abrir", "abre", "open"],
        )
        self.weather = FakeTool(
            name="get_weather",
            description="Obtiene el clima actual",
            keywords=["clima", "tiempo"],
        )

    def test_keyword_match_scores_higher(self):
        ranked = rank_tools("abre vscode", [self.open_app, self.weather])
        self.assertEqual(ranked[0]["tool"].name, "open_app")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_capability_overlap_boosts_score(self):
        music_tool = FakeTool(name="play_music", capabilities=["music"])
        other_tool = FakeTool(name="other")
        ranked = rank_tools(
            "quiero escuchar musica",
            [music_tool, other_tool],
            desired_capabilities=["music"],
        )
        self.assertEqual(ranked[0]["tool"].name, "play_music")

    def test_select_best_tool_respects_threshold(self):
        best, ranked = select_best_tool("algo random sin relacion", [self.open_app, self.weather])
        self.assertIsNone(best)
        self.assertEqual(len(ranked), 2)

    def test_select_best_tool_returns_match_above_threshold(self):
        best, _ = select_best_tool("abre el navegador", [self.open_app, self.weather])
        self.assertIsNotNone(best)
        self.assertEqual(best["tool"].name, "open_app")


if __name__ == "__main__":
    unittest.main()
