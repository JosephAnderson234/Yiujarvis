import unittest

from src.intent import build_action_plan, classify_intent, extract_targets, is_direct_command, is_shutdown_command


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


class KeywordBoundaryRegressionTests(unittest.TestCase):
    def test_substring_of_open_keyword_is_not_open(self):
        self.assertNotEqual(classify_intent("qué es openai"), "open_app")

    def test_substring_of_close_keyword_is_not_close(self):
        self.assertNotEqual(classify_intent("ayúdame a determinar el costo"), "close_program")

    def test_shutdown_word_inside_sentence_does_not_shut_down(self):
        self.assertNotEqual(classify_intent("quiero salir a correr"), "shutdown")
        self.assertFalse(is_shutdown_command("quiero salir a correr"))

    def test_shutdown_with_wake_word_and_punctuation(self):
        self.assertTrue(is_shutdown_command("Jarvis, apágate!"))
        self.assertTrue(is_shutdown_command("salir"))

    def test_music_question_is_not_music_command(self):
        self.assertEqual(classify_intent("qué canción me recomiendas?"), "ask_info")


class DirectCommandTests(unittest.TestCase):
    def test_short_open_command_is_direct(self):
        self.assertTrue(is_direct_command("abre vscode y spotify"))

    def test_wake_word_prefix_is_allowed(self):
        self.assertTrue(is_direct_command("jarvis, cierra spotify"))

    def test_question_is_not_direct(self):
        self.assertFalse(is_direct_command("abre spotify?"))

    def test_verb_in_middle_is_not_direct(self):
        self.assertFalse(is_direct_command("me puedes decir si conviene que abra spotify"))

    def test_long_request_goes_to_llm(self):
        self.assertFalse(is_direct_command("abre el navegador y busca el clima de mañana en lima y luego dime"))


class ExtractTargetsTests(unittest.TestCase):
    def test_extracts_single_target(self):
        self.assertEqual(extract_targets("abre vscode"), ["vscode"])

    def test_keyword_inside_target_name_is_kept(self):
        self.assertEqual(extract_targets("abre cabrera"), ["cabrera"])

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
