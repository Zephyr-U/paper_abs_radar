# paper_abs_radar

`paper_abs_radar` is a local Python CLI for monitoring selected IEEE and Nature-family journals. The current minimal workflow collects public paper metadata and abstracts, then exports CSV, JSON, and Obsidian-compatible Markdown.

It does not download paid PDFs, automate browser sessions, use IEEE login flows, or scrape paywalled pages.

## Sources

The v0.1 source flow is:

1. OpenAlex as the required journal monitor by ISSN and date range.
2. Semantic Scholar for DOI/title enrichment.
3. Crossref for DOI, date, publisher metadata, and deposited abstracts.
4. Springer Nature Metadata API for optional Nature/Springer abstract enrichment.

IEEE Xplore API access is not required.

## Setup

```bash
pip install -r requirements.txt
```

Springer Nature enrichment is optional:

```bash
export SPRINGER_API_KEY="your_key_here"
```

If `SPRINGER_API_KEY` is missing, the CLI logs a warning and continues.

## Usage

```bash
python -m src.main --config config.yaml
python -m src.main --config config.yaml --no-enrich
python -m src.main --config config.yaml --mode backfill --backfill-years 5 --no-enrich
python -m src.main --config config.yaml --mode backfill --backfill-years 5 --no-enrich --enrich-abstracts
python -m src.main --config config.yaml --mode seed-month --issue-month 2026-05
python -m src.main --config config.yaml --mode check-update
python -m src.main --config config.yaml --mode check-update --journal JSSC --obsidian-dir "/path/to/ASIC/Paper Fetch"
python -m src.main --config config.yaml --mode enrich-state-abstracts --journal JSSC
python -m src.main --config config.yaml --journal JSSC
python -m src.main --config config.yaml --no-springer
```

For the minimal JSSC-only workflow, use `--no-enrich` first. It fetches all OpenAlex pages for the configured JSSC ISSN and skips slower enrichment APIs.
Add `--enrich-abstracts` when you want to fill missing abstracts through OpenAlex DOI lookup first, then Crossref and Semantic Scholar. The cache defaults to `output/cache/abstracts.json`.
Use `--mode enrich-state-abstracts` to fill abstracts in an existing monthly/update baseline JSON under `output/state/`.
`check-update` writes a machine draft named `YYYY-MM-DD_JSSC_issue_summary_draft.md`; Codex should use that draft and the state JSON to write the final polished Obsidian note manually.

## JSSC Monthly Update Workflow

The JSSC v0.1 workflow is intentionally split into a machine draft and a Codex-polished Obsidian note.

### One-time or reset baseline

Seed the local baseline from a known issue month:

```bash
python -m src.main --config config.yaml --mode seed-month --journal JSSC --issue-month 2026-05
python -m src.main --config config.yaml --mode enrich-state-abstracts --journal JSSC
```

This writes and enriches:

```text
output/state/JSSC_papers.json
```

### Recurring update check

Run this weekly or manually. It checks the last 30 days and only writes a draft when the number of new papers is greater than the update threshold, default `20`.

```bash
python -m src.main --config config.yaml --mode check-update --journal JSSC --obsidian-dir "/path/to/Obsidian/ASIC/Paper Fetch"
```

When triggered, the CLI:

1. Fetches recent JSSC records from Crossref.
2. Deduplicates against `output/state/JSSC_papers.json`.
3. Enriches new papers with abstracts through OpenAlex DOI lookup first, then Crossref and Semantic Scholar.
4. Writes a machine draft:

```text
output/summaries/YYYY-MM-DD_JSSC_issue_summary_draft.md
```

5. Updates the local baseline state.

The CLI does not write the polished Obsidian summary automatically. Codex should read the draft and state JSON, then manually write the final note to:

```text
/path/to/Obsidian/ASIC/Paper Fetch/YYYY-MM-DD_JSSC_issue_summary.md
```

### Summary rules

- Classification is title-keyword based.
- Abstracts are used only for focused summary drafting.
- Category counts are non-exclusive, so totals may exceed the article count.
- Do not keep representative-paper sections in the final note.
- The final note should contain:
  - `Circuit Topic Distribution`
  - `Application Distribution`
  - `Focused Abstract Summaries`
- For focused summaries, Codex should write Chinese bullets in this format:

```text
- 針對問題:
- 技術/方法:
- 達到效果:
```

Focused summaries should cover:

- `Implantable / neural / biomedical`
- `Precision analog / references / sensors`
- `Ultra-low-power / always-on / IoT`
- one reproducible `Additional sample`

### Monthly update checklist

- Run `check-update --journal JSSC`.
- Confirm whether new papers are greater than `20`.
- If a draft is created, confirm abstract coverage in the log.
- Open `output/summaries/YYYY-MM-DD_JSSC_issue_summary_draft.md`.
- Use Codex to polish focused summaries into Chinese `問題 / 方法 / 效果` format.
- Save the final note under the Obsidian root folder `Paper Fetch`.
- Confirm `output/state/JSSC_papers.json` has been updated.

The minimal backfill output intentionally contains only:

```text
title, authors, venue, venue_short, year, publication_date, doi, url, abstract
```

Outputs are written as:

```text
output/YYYY-MM-DD_MODE_FROM_to_TO_papers.csv
output/YYYY-MM-DD_MODE_FROM_to_TO_papers.json
output/YYYY-MM-DD_MODE_FROM_to_TO_paper_metadata.md
```

## Testing

The tests use the Python standard library runner and do not require live network access or API keys.

```bash
python -m unittest discover -s tests -v
```

## Notes

- Missing abstracts are allowed.
- Missing DOIs are allowed.
- Source failures log warnings and do not abort the full run.
- No LLM API is used in v0.1.
