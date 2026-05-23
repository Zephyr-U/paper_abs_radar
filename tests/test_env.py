import os
import tempfile
import unittest
from pathlib import Path

from src.env import load_env_file


class EnvTests(unittest.TestCase):
    def test_load_env_file_sets_exported_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".paper_abs_radar.env"
            env_path.write_text('export SPRINGER_API_KEY="test-key"\n', encoding="utf-8")
            old_value = os.environ.pop("SPRINGER_API_KEY", None)
            try:
                load_env_file(env_path)
                self.assertEqual(os.environ["SPRINGER_API_KEY"], "test-key")
            finally:
                os.environ.pop("SPRINGER_API_KEY", None)
                if old_value is not None:
                    os.environ["SPRINGER_API_KEY"] = old_value

    def test_load_env_file_does_not_override_existing_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".paper_abs_radar.env"
            env_path.write_text('export SPRINGER_API_KEY="file-key"\n', encoding="utf-8")
            old_value = os.environ.get("SPRINGER_API_KEY")
            os.environ["SPRINGER_API_KEY"] = "existing-key"
            try:
                load_env_file(env_path)
                self.assertEqual(os.environ["SPRINGER_API_KEY"], "existing-key")
            finally:
                if old_value is None:
                    os.environ.pop("SPRINGER_API_KEY", None)
                else:
                    os.environ["SPRINGER_API_KEY"] = old_value
