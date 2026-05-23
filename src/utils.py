from __future__ import annotations

import logging
import time
from typing import Any, Optional

LOGGER = logging.getLogger(__name__)
USER_AGENT = "paper_abs_radar/0.1 (mailto:metadata-only@example.com)"


def get_json(
    url: str,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 20,
    max_retries: int = 3,
) -> Optional[dict[str, Any]]:
    try:
        import requests
    except ImportError:
        LOGGER.warning("The requests package is required for live API calls")
        return None

    merged_headers = {"User-Agent": USER_AGENT}
    if headers:
        merged_headers.update(headers)

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, headers=merged_headers, timeout=timeout)
            if response.status_code == 429:
                sleep_for = min(30, 2**attempt)
                LOGGER.warning("Rate limited by %s; sleeping %ss", url, sleep_for)
                time.sleep(sleep_for)
                continue
            if 400 <= response.status_code < 500:
                LOGGER.warning("Skipping %s after client error %s", url, response.status_code)
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            if attempt == max_retries:
                LOGGER.warning("Failed GET %s after %s attempts: %s", url, max_retries, exc)
                return None
            time.sleep(2**attempt)
    return None


def first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    cleaned = " ".join(str(text).split())
    return cleaned or None
