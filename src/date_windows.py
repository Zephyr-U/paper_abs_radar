from __future__ import annotations

from datetime import date, timedelta


def resolve_date_window(
    mode: str,
    today: date,
    backfill_years: int,
) -> tuple[str, str]:
    if mode == "backfill":
        return _replace_year_safely(today, today.year - backfill_years).isoformat(), today.isoformat()
    raise ValueError(f"Unknown run mode: {mode}")


def build_run_label(mode: str, from_date: str, to_date: str) -> str:
    return f"{to_date}_{mode}_{from_date}_to_{to_date}"


def _replace_year_safely(value: date, year: int) -> date:
    try:
        return value.replace(year=year)
    except ValueError:
        return value.replace(year=year, day=28)
