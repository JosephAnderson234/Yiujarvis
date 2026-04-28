import unittest

from src.tools import close_program


class ToolTests(unittest.TestCase):
    def test_blacklisted_process_cannot_be_closed(self):
        self.assertIn("No se permite cerrar", close_program("explorer"))


if __name__ == "__main__":
    unittest.main()