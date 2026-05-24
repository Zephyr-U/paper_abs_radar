import unittest

from src.config import load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_includes_tracked_journals(self):
        config = load_config("config.yaml")
        journals = {journal.short: journal for journal in config.journals}

        self.assertIn("JSSC", journals)
        self.assertIn("JSSC-L", journals)
        self.assertEqual(journals["JSSC-L"].name, "IEEE Solid-State Circuits Letters")
        self.assertEqual(journals["JSSC-L"].issn, "2573-9603")
        self.assertIn("TBioCAS", journals)
        self.assertEqual(journals["TBioCAS"].name, "IEEE Transactions on Biomedical Circuits and Systems")
        self.assertEqual(journals["TBioCAS"].issn, "1932-4545")
        self.assertIn("Nature Sensors", journals)
        self.assertEqual(journals["Nature Sensors"].name, "Nature Sensors")
        self.assertEqual(journals["Nature Sensors"].issn, "3059-4499")
        self.assertIn("Nature BME", journals)
        self.assertEqual(journals["Nature BME"].name, "Nature Biomedical Engineering")
        self.assertEqual(journals["Nature BME"].issn, "2157-846X")
