import unittest
from unittest.mock import Mock, patch

from src.utils import get_json


class GetJsonTests(unittest.TestCase):
    def test_client_error_is_not_retried(self):
        response = Mock()
        response.status_code = 404
        response.raise_for_status.side_effect = RuntimeError("not found")

        with patch("requests.get", return_value=response) as mock_get:
            self.assertIsNone(get_json("https://example.test"))

        self.assertEqual(mock_get.call_count, 1)
