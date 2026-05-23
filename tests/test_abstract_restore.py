import unittest

from src.sources.openalex import restore_openalex_abstract


class OpenAlexAbstractRestoreTests(unittest.TestCase):
    def test_restore_openalex_abstract_orders_words_by_position(self):
        inverted = {
            "circuit": [2],
            "A": [0],
            "biomedical": [1],
            "works": [3],
        }

        self.assertEqual(restore_openalex_abstract(inverted), "A biomedical circuit works")

    def test_restore_openalex_abstract_returns_none_for_missing_index(self):
        self.assertIsNone(restore_openalex_abstract(None))
        self.assertIsNone(restore_openalex_abstract({}))


if __name__ == "__main__":
    unittest.main()
