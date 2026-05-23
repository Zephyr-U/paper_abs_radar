from __future__ import annotations

import argparse
import logging
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

from src.abstracts import enrich_missing_abstracts
from src.config import load_config
from src.date_windows import build_run_label, compact_date_label, resolve_date_window
from src.enrich import deduplicate_and_merge, enrich_papers
from src.export import export_outputs
from src.sources.crossref import search_crossref_by_issn
from src.sources.openalex import search_openalex_by_issn
from src.update import apply_update_if_threshold_met, enrich_state_abstracts, save_papers_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch recent paper metadata and abstracts.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--mode",
        choices=["backfill", "seed-month", "seed-window", "check-update", "enrich-state-abstracts"],
        default="check-update",
        help="Run mode. backfill uses OpenAlex; seed-month/check-update use Crossref update state.",
    )
    parser.add_argument("--backfill-years", type=int, default=5, help="Years to fetch for --mode backfill")
    parser.add_argument("--issue-month", help="Issue month for seed-month, e.g. 2026-05")
    parser.add_argument("--from", dest="from_date", help="Start date for seed-window, e.g. 2026-03-01")
    parser.add_argument("--to", dest="to_date", help="End date for seed-window, e.g. 2026-05-23")
    parser.add_argument("--lookback-days", type=int, help="Days to inspect for check-update")
    parser.add_argument("--update-threshold", type=int, help="Write summary and update state only above this new-paper count")
    parser.add_argument("--state-dir", default="output/state", help="Directory for local update baseline JSON")
    parser.add_argument("--summary-dir", default="output/summaries", help="Directory for generated issue summaries")
    parser.add_argument("--obsidian-dir", help="Optional Obsidian output directory for Codex-polished summaries")
    parser.add_argument("--journal", help="Filter by journal short name, e.g. JSSC")
    parser.add_argument("--no-enrich", action="store_true", help="Skip enrichment and export OpenAlex results only")
    parser.add_argument("--enrich-abstracts", action="store_true", help="Fill missing abstracts using OpenAlex, Crossref, then Semantic Scholar")
    parser.add_argument("--allow-title-search", action="store_true", help="Allow Semantic Scholar title search when DOI lookup cannot fill an abstract")
    parser.add_argument("--abstract-cache", default="output/cache/abstracts.json", help="Cache path for abstract enrichment")
    parser.add_argument("--no-springer", action="store_true", help="Disable Springer Nature enrichment")
    parser.add_argument("--log-level", default="INFO", help="Python logging level")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s: %(message)s")
    config = load_config(args.config)
    journals = config.journals
    if args.journal:
        wanted = args.journal.lower()
        journals = [journal for journal in journals if journal.short.lower() == wanted]
    if not journals:
        logging.warning("No journals matched the requested filter")
        return 0

    if args.mode == "seed-month":
        if not args.issue_month:
            raise SystemExit("--issue-month is required for seed-month, e.g. --issue-month 2026-05")
        for journal in journals:
            from_date, to_date = _month_bounds(args.issue_month)
            logging.info("Seeding %s state from Crossref %s to %s", journal.short, from_date, to_date)
            papers = search_crossref_by_issn(
                journal.issn,
                from_date,
                to_date,
                date_field=crossref_date_field_for_journal_short(journal.short),
            )
            state_path = Path(args.state_dir) / f"{journal.short}_papers.json"
            save_papers_json(state_path, deduplicate_and_merge(papers))
            logging.info("Wrote %s (%s papers)", state_path, len(papers))
        return 0

    if args.mode == "seed-window":
        today = date.today()
        for journal in journals:
            from_date, to_date = seed_window_bounds_for_journal_short(
                journal.short,
                today,
                args.from_date,
                args.to_date,
                args.lookback_days,
            )
            logging.info("Seeding %s state from Crossref %s to %s", journal.short, from_date, to_date)
            papers = search_crossref_by_issn(
                journal.issn,
                from_date,
                to_date,
                date_field=crossref_date_field_for_journal_short(journal.short),
            )
            state_path = Path(args.state_dir) / f"{journal.short}_papers.json"
            save_papers_json(state_path, deduplicate_and_merge(papers))
            logging.info("Wrote %s (%s papers)", state_path, len(papers))
        return 0

    if args.mode == "check-update":
        today = date.today()
        for journal in journals:
            lookback_days, update_threshold = update_settings_for_journal_short(
                journal.short,
                args.lookback_days,
                args.update_threshold,
            )
            from_date = (today - timedelta(days=lookback_days)).isoformat()
            to_date = today.isoformat()
            logging.info("Checking %s Crossref updates from %s to %s", journal.short, from_date, to_date)
            current = deduplicate_and_merge(
                search_crossref_by_issn(
                    journal.issn,
                    from_date,
                    to_date,
                    date_field=crossref_date_field_for_journal_short(journal.short),
                )
            )
            state_path = Path(args.state_dir) / f"{journal.short}_papers.json"
            summary_path = Path(args.summary_dir) / f"{compact_date_label(to_date)}_{journal.short}_issue_summary_draft.md"
            result = apply_update_if_threshold_met(
                state_path,
                summary_path,
                current,
                threshold=update_threshold,
                cache_path=Path(args.abstract_cache),
                allow_title_search=args.allow_title_search,
                summary_profile=summary_profile_for_journal_short(journal.short),
            )
            logging.info("New papers for %s: %s", journal.short, result.new_count)
            if result.summary_written:
                logging.info(
                    "Abstracts for new papers: %s/%s before, %s/%s after",
                    result.with_abstract_before,
                    result.new_count,
                    result.with_abstract_after,
                    result.new_count,
                )
                logging.info("Wrote draft summary and updated state: %s", result.summary_path)
                if args.obsidian_dir:
                    logging.info("Obsidian dir configured for Codex-polished summaries: %s", args.obsidian_dir)
            else:
                logging.info("No state update because new paper count did not exceed %s", update_threshold)
        return 0

    if args.mode == "enrich-state-abstracts":
        for journal in journals:
            state_path = Path(args.state_dir) / f"{journal.short}_papers.json"
            logging.info("Enriching abstracts in %s", state_path)
            result = enrich_state_abstracts(
                state_path,
                cache_path=Path(args.abstract_cache),
                allow_title_search=args.allow_title_search,
            )
            logging.info(
                "%s abstracts: %s/%s before, %s/%s after",
                journal.short,
                result.with_abstract_before,
                result.total,
                result.with_abstract_after,
                result.total,
            )
        return 0

    from_date, to_date = resolve_date_window(
        args.mode,
        today=date.today(),
        backfill_years=args.backfill_years,
    )
    logging.info("Using date window %s to %s (%s)", from_date, to_date, args.mode)

    papers = []
    for journal in journals:
        logging.info("Fetching OpenAlex records for %s (%s)", journal.short, journal.issn)
        papers.extend(
            search_openalex_by_issn(
                journal.issn,
                from_date,
                to_date,
                venue_short=journal.short,
            )
        )

    merged = deduplicate_and_merge(papers)
    enriched = merged if args.no_enrich else enrich_papers(merged, use_springer=not args.no_springer)
    if args.enrich_abstracts:
        enriched = enrich_missing_abstracts(
            enriched,
            cache_path=Path(args.abstract_cache),
            allow_title_search=args.allow_title_search,
        )
    run_label = build_run_label(args.mode, from_date, to_date)
    paths = export_outputs(
        enriched,
        config.output_dir,
        run_label,
        config.markdown_filename,
        config.csv_filename,
        config.json_filename,
    )
    logging.info("Wrote %s", paths["markdown"])
    logging.info("Wrote %s", paths["csv"])
    logging.info("Wrote %s", paths["json"])
    return 0


def _month_bounds(issue_month: str) -> tuple[str, str]:
    year_text, month_text = issue_month.split("-", 1)
    year = int(year_text)
    month = int(month_text)
    last_day = monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def crossref_date_field_for_journal_short(journal_short: str) -> str:
    if journal_short.upper() == "JSSC-L":
        return "created"
    return "published"


def update_settings_for_journal_short(
    journal_short: str,
    explicit_lookback_days: int | None,
    explicit_update_threshold: int | None,
) -> tuple[int, int]:
    if journal_short.upper() in {"JSSC-L", "NATURE SENSORS"}:
        default_lookback_days = 90
        default_update_threshold = 9
    else:
        default_lookback_days = 30
        default_update_threshold = 20
    return (
        explicit_lookback_days if explicit_lookback_days is not None else default_lookback_days,
        explicit_update_threshold if explicit_update_threshold is not None else default_update_threshold,
    )


def summary_profile_for_journal_short(journal_short: str) -> str:
    if journal_short.upper() == "NATURE SENSORS":
        return "nature_sensors"
    return "circuits"


def seed_window_bounds_for_journal_short(
    journal_short: str,
    today: date,
    explicit_from_date: str | None,
    explicit_to_date: str | None,
    explicit_lookback_days: int | None,
) -> tuple[str, str]:
    if explicit_from_date and explicit_to_date:
        return explicit_from_date, explicit_to_date
    if explicit_from_date or explicit_to_date:
        raise ValueError("--from and --to must be provided together for seed-window")
    lookback_days, _update_threshold = update_settings_for_journal_short(
        journal_short,
        explicit_lookback_days,
        None,
    )
    return (today - timedelta(days=lookback_days)).isoformat(), today.isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
