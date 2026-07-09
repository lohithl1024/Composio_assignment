# Integration Radar

Agent-assisted research workflow for the Composio AI Product Ops take-home assignment.

The project is designed to classify 100 apps by auth, credential access, API surface, MCP evidence, and practical Composio toolkit buildability. The final output is a single HTML case study plus structured CSV/JSON research artifacts.

## Current Foundation

This first pass creates:

- typed row schema in `src/models`
- access/API/buildability rubrics in `docs/schema_and_rubrics.md`
- static case-study skeleton in `web/case_study.html`
- data directories for input, processed outputs, and verification notes
- bootstrap module in `src/bootstrap_records.py`
- validated stub dataset in `data/processed/app_records.stub.jsonl`
- source discovery module in `src/discover_sources.py`
- deterministic discovery output in `data/processed/app_records.discovered.jsonl`
- source packet builder in `src/source_packet.py`
- first-pass extraction module in `src/extract_record.py`
- extracted dataset in `data/processed/app_records.extracted.jsonl`
- sampled verification module in `src/verify_record.py`
- verified dataset in `data/processed/app_records.verified.jsonl`
- verification audit artifacts in `data/processed/verification_sample.*` and `data/processed/verification_summary.json`
- analysis module in `src/run_analysis.py`
- final table flattener in `src/build_visible_dataset.py`
- analysis outputs in `data/analysis/`
- reviewer-facing table data in `data/final/`

## Run the Bootstrap Step

From the project root:

```bash
python3 -m src.bootstrap_records
```

Custom paths are supported:

```bash
python3 -m src.bootstrap_records \
  --input data/input/apps.csv \
  --output data/processed/app_records.stub.jsonl
```

The bootstrap step reads the 100-app input list and emits one validated JSONL record per app with deterministic fields filled and research fields initialized as unknown/pending.

Initial workflow defaults:

- `research_status`: `pending`
- `verification.status`: `not_checked`
- `workflow.agent_confidence`: `low`
- `workflow.buildability_confidence`: `low`
- `workflow.human_review_required`: `unclear`
- `workflow.source_count`: `0`

## Run Source Discovery

From the project root, after bootstrap:

```bash
python3 -m src.discover_sources
```

Custom paths are supported:

```bash
python3 -m src.discover_sources \
  --input data/processed/app_records.stub.jsonl \
  --output data/processed/app_records.discovered.jsonl
```

The discovery step only attaches source URLs. It does not classify auth, API breadth, access model, MCP status, or buildability.

Current deterministic discovery coverage:

- `100/100` records written
- `88/100` records have developer docs and/or API docs attached
- remaining partial rows keep only the official site until targeted web-assisted discovery is added

Fields updated:

- `sources.official_site`
- `sources.developer_docs`
- `sources.api_docs`
- `sources.auth_docs`
- `sources.pricing_or_access`
- `sources.mcp_url`
- `sources.additional_source_urls`
- `sources.discovered_sources`
- `workflow.source_count`
- `workflow.research_status = discovered`

## Run First-Pass Extraction

From the project root, after discovery:

```bash
python3 -m src.extract_record
```

Custom paths are supported:

```bash
python3 -m src.extract_record \
  --input data/processed/app_records.discovered.jsonl \
  --output data/processed/app_records.extracted.jsonl
```

By default, extraction uses compact packets built from discovered URL/title/source metadata and deterministic rubric heuristics. To fetch source page text before extraction, run:

```bash
python3 -m src.extract_record --fetch
```

The extraction step fills first-pass research fields, but it does not perform verifier-style challenge or human correction. Those belong in Module 4.

Current first-pass extraction output:

- `100/100` records extracted
- `99/100` records include at least one evidence item
- `88/100` medium-confidence rows
- `12/100` low-confidence rows flagged for human review

Fields updated:

- `one_line_description`
- `auth_methods`
- `primary_auth_for_toolkit`
- `auth_complexity`
- `auth_notes`
- `access.*`
- `api_surface.*`
- `mcp.*`
- `buildability.*`
- `evidence`
- `confidence`
- `workflow.research_status = extracted`
- `workflow.agent_confidence`
- `workflow.buildability_confidence`
- `workflow.human_review_required`

## Run Sampled Verification

From the project root, after extraction:

```bash
python3 -m src.verify_record
```

Custom paths are supported:

```bash
python3 -m src.verify_record \
  --input data/processed/app_records.extracted.jsonl \
  --output data/processed/app_records.verified.jsonl \
  --sample-jsonl data/processed/verification_sample.jsonl \
  --sample-csv data/processed/verification_sample.csv \
  --summary data/processed/verification_summary.json \
  --sample-size 20
```

The verification step has two layers:

1. Full-dataset sanity checks for contradictions such as `buildable_now` without a public API or official MCP without an MCP source.
2. A 20-app sampled audit that checks six field families: description, auth, access model, API surface, MCP status, and buildability.

The generated audit is a verification scaffold and manual QA queue. It intentionally keeps unresolved rows flagged instead of pretending weak evidence is resolved.

Current verification output:

- `100/100` verified records written
- `20` sampled apps
- `120` field-level checks in `verification_sample.csv`
- strict first-pass sampled field accuracy: `37.5%`
- first-pass correct-or-partial rate: `51.7%`
- post-verification resolved field rate: `51.7%`
- unresolved after verification: `48.3%`
- row outcomes: `14` flagged, `1` corrected, `5` partial

## Run Analysis

From the project root, after verification:

```bash
python3 -m src.run_analysis
```

This writes:

- `data/analysis/analysis_summary.json`
- `data/analysis/category_breakdown.csv`
- `data/analysis/buildability_distribution.csv`
- `data/analysis/access_distribution.csv`
- `data/analysis/auth_distribution.csv`
- `data/analysis/all_auth_distribution.csv`
- `data/analysis/blocker_counts.csv`
- `data/analysis/easy_wins.csv`
- `data/analysis/outreach_needed.csv`

Current headline outputs:

- `60.0%` classified as buildable-now in the current verified dataset
- top known primary auth path: `OAuth 2.0`
- most common non-trivial blocker: `admin_setup_required`
- `20` easy-win candidates
- `20` outreach-needed candidates

## Build Reviewer-Facing Dataset

From the project root, after verification:

```bash
python3 -m src.build_visible_dataset
```

This writes:

- `data/final/app_research_final.csv`
- `data/final/app_research_final.json`

The final table contains 100 flat rows with columns for app, category, description, auth, access model, API surface, MCP status, buildability verdict, blocker, confidence, verification status, evidence URLs, and short notes.

## Build Final HTML Case Study

From the project root, after analysis and visible dataset generation:

```bash
python3 -m src.build_case_study
```

This writes a self-contained reviewer page:

- `web/composio-analyzer/index.html`
- `web/composio-analyzer/dataset/index.html`
- `web/composio-analyzer/workflow/index.html`
- `web/case_study.html` as a compatibility copy of the overview

The generated HTML embeds:

- `data/analysis/analysis_summary.json`
- `data/final/app_research_final.json`
- `data/processed/verification_summary.json`

Because the data is embedded at build time, the page can be opened directly in a browser or deployed as a static file without a backend server.

Final route structure:

- `/composio-analyzer`: portfolio-style overview page with hero, agents, architecture, and output tabs
- `/composio-analyzer/dataset`: searchable 100-app matrix with row detail panel
- `/composio-analyzer/workflow`: full agent workflow, verification metrics, and audit examples

## Pipeline

1. `bootstrap_records`: create canonical stub records from the 100-app input list.
2. `discover_sources`: attach official docs/API/auth/access/MCP URLs without classification.
3. `extract_record`: fill auth, access, API, MCP, buildability, and evidence fields.
4. `verify_record`: challenge claims, adjust confidence, and flag human review rows.
5. `run_analysis`: compute patterns, distributions, shortlists, and error modes.
6. `build_visible_dataset`: flatten the rich records into reviewer-facing CSV/HTML tables.
7. `build_case_study`: render the final HTML case study.

## Output Files

- `data/processed/app_records.stub.jsonl`
- `data/processed/app_records.discovered.jsonl`
- `data/processed/app_records.extracted.jsonl`
- `data/processed/app_records.verified.jsonl`
- `data/processed/verification_sample.jsonl`
- `data/processed/verification_sample.csv`
- `data/processed/verification_summary.json`
- `data/analysis/analysis_summary.json`
- `data/analysis/*.csv`
- `data/final/app_research_final.csv`
- `data/final/app_research_final.json`
- `web/composio-analyzer/index.html`
- `web/composio-analyzer/dataset/index.html`
- `web/composio-analyzer/workflow/index.html`
- `web/case_study.html`

## Key Principle

The research system should distinguish:

- documented facts from buildability judgments
- existing MCP support from MCP/toolkit suitability
- public API existence from practical credential access
- first-pass agent output from verified final findings
