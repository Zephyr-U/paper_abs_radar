import unittest

from src.config import load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_includes_jssc_and_jssc_l(self):
        config = load_config("config.yaml")
        journals = {journal.short: journal for journal in config.journals}

        self.assertIn("JSSC", journals)
        self.assertIn("JSSC-L", journals)
        self.assertEqual(journals["JSSC-L"].name, "IEEE Solid-State Circuits Letters")
        self.assertEqual(journals["JSSC-L"].issn, "2573-9603")
