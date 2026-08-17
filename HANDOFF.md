# IRCC PR-by-Country Dashboard — Automation Handoff

## Context

Nicholas is an RCIC running an immigration consulting practice (hogavisa.com). He has an existing interactive dashboard that visualizes IRCC permanent resident admissions by country over time. Right now the pipeline is manual: a Python script reads a hand-cleaned CSV and generates a standalone Plotly HTML file, which gets uploaded somewhere ad hoc.

The goal of this thread was to figure out what to bring forward. This document is the handoff — pick up the automation build from here.

## End goal (four things)

1. **Host the project on GitHub** — a real repo, not loose files.
2. **Host the live dashboard on hogavisa.com** — his site runs on Wix. The likely pattern is a GitHub Pages (or similar) URL embedded via a Wix iframe, matching how his other blog widgets are delivered — see "Design constraints" below.
3. **Automate backend downloading of the latest IRCC dataset** — nothing currently fetches new data. This needs to be built from scratch: identify the correct IRCC open data source for PR admissions by country/month, and write a fetch script.
4. **Automate cleaning + dashboard rebuild + publish** — chain fetch → clean → build → deploy, on a schedule (GitHub Actions cron is the natural choice).

None of steps 3–4 exist yet. Only the clean/build half (step "clean" partially, and "build") has working code, described below.

## What already exists (starting files)

Two files are the actual working core and should be treated as the starting point:

- **`ircc_dashboard_pr_by_country.py`** — the build script. Reads a long-format CSV (`Country, Year, Month, Date, Admissions`), aggregates annual totals / YoY / country shares, and emits a single self-contained `pr_dashboard.html` (Plotly, loaded via CDN `cdn.plot.ly/plotly-2.27.0.min.js`, ~280 lines of generated HTML/JS). CLI: `python ircc_dashboard_pr_by_country.py <long_clean_csv> [--countries "A,B,C"] [--output_dir ./outputs]`. Defaults to showing Hong Kong SAR, China PRC, Vietnam. Auto-detects and excludes a partial current year from aggregations.
- **`pr_citz_long_clean.csv`** — the cleaned long-format source data the script consumes. 29,296 rows, tidy format, this is the source of truth for the build step.

Two other files exist but are lower priority / not required by the build script:

- `pr_citz_wide_clean.csv` — a pivoted/wide export of the same data. The build script does not read this. Keep only if useful for manual spot-checking the cleaning logic.
- `pr_dashboard__1_.html` — the current build output. Fully regeneratable from the two files above; useful only as a visual baseline to diff against.

**Not yet built at all:**
- The downloader (fetch latest IRCC dataset — source/endpoint not yet identified, needs research)
- Any raw-to-clean transformation script (the long CSV in hand is already clean; the raw IRCC export format it comes from hasn't been characterized yet)
- Repo scaffolding (`requirements.txt`, `README.md`, `.gitignore`, folder layout e.g. `/data`, `/scripts`, `/output`, `/.github/workflows`)
- GitHub Actions workflow (cron-triggered fetch → clean → build → commit/deploy)
- Deployment/publish step to make the built HTML live and embeddable on hogavisa.com

## Design constraints to respect

Nicholas has an established convention for interactive widgets on hogavisa.com (documented in his blog production skill):

- Standalone HTML files, no external dependencies where possible, ES5-compatible JS, built for **Wix iframe embedding**.
- The current dashboard breaks this pattern by loading Plotly from a CDN. That's a **deliberate decision point, not an oversight** — flag it back to Nicholas rather than silently "fixing" it. Options: keep the CDN dependency (fine in an iframe, just inconsistent with his other widgets), vendor/bundle Plotly locally, or rebuild the chart logic without Plotly to match his no-dependency convention. Ask before choosing.
- No live API calls from the client-side widget itself — his other widgets use pre-written approved content only. The dashboard is a partial exception since it's inherently data-driven, but confirm whether he wants the *data* baked in at build time (current approach — safe, no live calls) versus fetched live in-browser (would break convention and needs his sign-off).
- Dark navy / amber gold design system exists for his blog widgets (`#0d1f3c` cards, `#071529` expanded panels, `#f0c060` titles, `#c8860a` accents) — check with Nicholas whether the dashboard should be restyled to match, since currently it likely uses its own Plotly default styling.

## Suggested first session tasks for Claude Code

1. Set up repo structure and drop in the two working files (`.py` script, long clean CSV) as the initial commit.
2. Research and confirm the correct IRCC open data source/endpoint for PR admissions by country and month (this needs verification — don't assume a URL).
3. Draft the fetch script and a raw-to-clean transform (matching the existing long CSV schema) once the source format is confirmed.
4. Scaffold the GitHub Actions workflow (schedule, steps, secrets if needed).
5. Confirm the Plotly-CDN-vs-no-dependency decision and the Wix embedding approach with Nicholas before finalizing the publish step.

## Open questions for Nicholas (don't guess on these)

- Exact IRCC dataset/endpoint to poll for updates, and how often it actually updates (monthly cadence, presumably).
- Where the built HTML should actually live for hogavisa.com to embed (GitHub Pages URL, other static host, etc.).
- Whether to keep the Plotly CDN dependency or rebuild to match his no-external-dependency widget convention.
- Whether he wants dashboard styling to match his blog's dark navy/amber design system.
