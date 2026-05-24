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
python -m src.main --config config.yaml --mode seed-window --journal JSSC-L
python -m src.main --config config.yaml --mode check-update
python -m src.main --config config.yaml --mode check-update --journal JSSC --obsidian-dir "/path/to/ASIC/Paper Fetch"
python -m src.main --config config.yaml --mode check-update --journal JSSC-L
python -m src.main --config config.yaml --mode enrich-state-abstracts --journal JSSC
python -m src.main --config config.yaml --journal JSSC
python -m src.main --config config.yaml --no-springer
```

For the minimal JSSC-only workflow, use `--no-enrich` first. It fetches all OpenAlex pages for the configured JSSC ISSN and skips slower enrichment APIs.
Add `--enrich-abstracts` when you want to fill missing abstracts through OpenAlex DOI lookup first, then Crossref and Semantic Scholar. The cache defaults to `output/cache/abstracts.json`.
Use `--mode enrich-state-abstracts` to fill abstracts in an existing monthly/update baseline JSON under `output/state/`.
`check-update` writes a machine draft named `YYMMDD_JSSC_issue_summary_draft.md`; Codex should use that draft and the state JSON to write the final polished Obsidian note manually.

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
output/summaries/YYMMDD_JSSC_issue_summary_draft.md
```

5. Updates the local baseline state.

The CLI does not write the polished Obsidian summary automatically. Codex should read the draft and state JSON, then manually write the final note to:

```text
/path/to/Obsidian/ASIC/Paper Fetch/YYMMDD_JSSC_issue_summary.md
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
- Open `output/summaries/YYMMDD_JSSC_issue_summary_draft.md`.
- Use Codex to polish focused summaries into Chinese `問題 / 方法 / 效果` format.
- Save the final note under the Obsidian root folder `Paper Fetch`.
- Confirm `output/state/JSSC_papers.json` has been updated.

The minimal backfill output intentionally contains only:

```text
title, authors, venue, venue_short, year, publication_date, doi, url, abstract
```

Outputs are written as:

```text
output/YYMMDD_MODE_FROM_to_TO_papers.csv
output/YYMMDD_MODE_FROM_to_TO_papers.json
output/YYMMDD_MODE_FROM_to_TO_paper_metadata.md
```

## JSSC-L Article-Count Update Workflow

`IEEE Solid-State Circuits Letters` (`JSSC-L`) is configured separately from JSSC because Crossref records for this journal often only expose year-level published dates. The update workflow therefore uses Crossref `created` dates for monthly/update windows.

JSSC-L also has a smaller rolling publication volume than JSSC, so its default `check-update` behavior is article-count based:

```text
lookback-days: 90
update-threshold: 9
```

Because the threshold rule is `new_count > threshold`, this means a JSSC-L draft is written after at least 10 unprocessed articles accumulate.

Seed or reset the JSSC-L baseline:

```bash
python -m src.main --config config.yaml --mode seed-window --journal JSSC-L
python -m src.main --config config.yaml --mode enrich-state-abstracts --journal JSSC-L
```

`seed-window` uses the same journal-specific lookback defaults as `check-update`, so JSSC-L seeds the most recent 90 days unless `--from` and `--to` are provided explicitly.

Run the rolling article-count update:

```bash
python -m src.main --config config.yaml --mode check-update --journal JSSC-L
```

When triggered, the draft is written to:

```text
output/summaries/YYMMDD_JSSC-L_issue_summary_draft.md
```

The polished Obsidian note should use:

```text
YYMMDD_JSSC-L_issue_summary.md
```

## Nature Sensors Article-Count Update Workflow

`Nature Sensors` uses the same article-count rolling update style as JSSC-L:

```text
lookback-days: 90
update-threshold: 9
```

This means a draft is written after at least 10 unprocessed Nature Sensors articles accumulate.

Nature-family DOI abstract enrichment uses Springer Nature Meta API v2. Set the Meta API key locally before running enrichment:

```bash
export SPRINGER_API_KEY="your_meta_api_key"
```

Seed or reset the Nature Sensors baseline:

```bash
python -m src.main --config config.yaml --mode seed-window --journal "Nature Sensors"
python -m src.main --config config.yaml --mode enrich-state-abstracts --journal "Nature Sensors"
```

Run the rolling article-count update:

```bash
python -m src.main --config config.yaml --mode check-update --journal "Nature Sensors"
```

Nature Sensors drafts use focused buckets tailored to wearable sensing and PPG/ML-adjacent work:

```text
Implantable / bioelectronic / neural
Wearable / epidermal / sweat / skin
Self-powered / wireless / battery-free
AI / in-sensor / neuromorphic computing
```

## TBioCAS Article-Count Update Workflow

`IEEE Transactions on Biomedical Circuits and Systems` (`TBioCAS`) uses the same article-count rolling update style as JSSC-L:

```text
lookback-days: 90
update-threshold: 9
```

This means a draft is written after at least 10 unprocessed TBioCAS articles accumulate.

Seed or reset the TBioCAS baseline:

```bash
python -m src.main --config config.yaml --mode seed-window --journal TBioCAS
python -m src.main --config config.yaml --mode enrich-state-abstracts --journal TBioCAS
```

Run the rolling article-count update:

```bash
python -m src.main --config config.yaml --mode check-update --journal TBioCAS
```

TBioCAS drafts use focused buckets tailored to biomedical circuits and systems:

```text
Implantable / neural interface
Wearable / biosignal acquisition
Biomedical AFE / sensor interface
Edge AI / biomedical signal processing
Wireless / power / closed-loop systems
```

## Nature Biomedical Engineering Filtered Update Workflow

`Nature Biomedical Engineering` (`Nature BME`) uses the same rolling article-count rule, but with an additional filter. The workflow reads Nature's public research-articles listing, enriches DOIs through Springer Nature Meta API, keeps research articles only, then stores only filtered papers in the local baseline.

```text
lookback-days: 90
update-threshold: 9
```

This means a draft is written after at least 10 new filtered Nature BME research articles accumulate.

Seed or reset the Nature BME filtered baseline:

```bash
python -m src.main --config config.yaml --mode seed-window --journal "Nature BME"
```

Run the rolling filtered update:

```bash
python -m src.main --config config.yaml --mode check-update --journal "Nature BME"
```

Nature BME drafts use these focused buckets:

```text
Wearable / bioelectronic sensing
Neural / neuromodulation / brain mapping
Biomedical imaging / sensing hardware
Organ/tissue-on-chip / microphysiological systems
Cardiovascular / hemodynamics / vascular monitoring
```

The filter intentionally excludes general gene therapy, drug delivery, immunotherapy, and general medical AI titles unless the title is clearly tied to sensing, imaging, biointerfaces, neural mapping, cardiovascular monitoring, or organ/tissue-chip systems.

Nature BME is a broader-view radar rather than a high-direct-relevance circuit feed. Treat it as a way to track biomedical system trends, application pull, and clinical translation opportunities that may inform ASIC/sensing work.

Final polished Obsidian summaries should use this format:

```text
# Nature BME ... Summary - YYMMDD

## 主題分佈

## Wearable / Bioelectronic Sensing
### Paper title
- DOI：
- 日期：
- 相關標籤：
- 針對問題：
- 使用技術/方法：
- 達到效果：

## Neural / Neuromodulation / Brain Mapping
...

## Biomedical Imaging / Sensing Hardware
...

## Organ/Tissue-on-Chip / Microphysiological Systems
...

## Cardiovascular / Bioelectronic Interface
...

## 對 ASIC / Sensing 方向的重點
```

Each paper should appear under one primary category only. Use `相關標籤` for cross-category context instead of duplicating papers across sections.

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
