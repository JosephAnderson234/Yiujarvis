import unittest

from src.intent import build_action_plan, classify_intent, extract_targets


class IntentClassificationTests(unittest.TestCase):
    def test_open_intent(self):
        self.assertEqual(classify_intent("abre vscode"), "open_app")

    def test_close_intent(self):
        self.assertEqual(classify_intent("cierra spotify"), "close_program")

    def test_save_preference_intent(self):
        self.assertEqual(classify_intent("recuerda que me gusta el cafe"), "save_preference")

    def test_shutdown_intent(self):
        self.assertEqual(classify_intent("apagate"), "shutdown")

    def test_music_intent(self):
        self.assertEqual(classify_intent("pon musica en spotify"), "music")

    def test_question_intent(self):
        self.assertEqual(classify_intent("que hora es?"), "ask_info")

    def test_chat_fallback(self):
        self.assertEqual(classify_intent("hola, todo bien"), "chat")


class ExtractTargetsTests(unittest.TestCase):
    def test_extracts_single_target(self):
        self.assertEqual(extract_targets("abre vscode"), ["vscode"])

    def test_extracts_multiple_targets(self):
        targets = extract_targets("abre vscode y spotify")
        self.assertEqual(targets, ["vscode", "spotify"])


class BuildActionPlanTests(unittest.TestCase):
    def test_open_app_plan_has_one_step_per_target(self):
        plan = build_action_plan("abre vscode y spotify")
        self.assertEqual(plan["intent"], "open_app")
        self.assertEqual(
            plan["steps"],
            [
                {"tool": "open_app", "arguments": {"app": "vscode"}},
                {"tool": "open_app", "arguments": {"app": "spotify"}},
            ],
        )

    def test_chat_intent_has_no_steps(self):
        plan = build_action_plan("hola")
        self.assertEqual(plan["steps"], [])


if __name__ == "__main__":
    unittest.main()
