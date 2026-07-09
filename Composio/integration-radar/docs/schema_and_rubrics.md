# Integration Radar Schema and Rubrics

This project evaluates whether 100 apps are practical candidates for Composio-style agent toolkits. The schema separates documented facts from judgment calls, and every important claim should point back to evidence.

## Row Blocks

Each app row is split into eight blocks:

1. **Identity**: app name, category, hint URL, one-line description.
2. **Sources**: official site, developer docs, auth docs, API docs, pricing/access docs, MCP evidence.
3. **Auth**: auth methods and notes.
4. **Access**: whether a developer can obtain useful credentials without sales, paid plans, or admin help.
5. **API Surface**: protocols, breadth, webhooks, and practical action coverage.
6. **MCP**: whether an official/community MCP exists, plus whether the app is suitable for MCP/toolkit wrapping.
7. **Buildability**: practical toolkit verdict, blocker, notes, and opportunity score.
8. **Evidence, Confidence, Verification**: cited support, confidence rationale, and QA status.

## Access Model

Use this enum for credential access:

- `self_serve_free_or_trial`: a developer can create an account, app, token, or OAuth client through a free plan or trial without talking to sales.
- `self_serve_paid_plan_required`: credentials are self-serve, but useful API access requires a paid plan.
- `admin_or_workspace_dependent`: API/auth is available, but setup usually requires an org owner, workspace admin, tenant admin, or customer-owned environment.
- `partner_or_contact_sales_gated`: useful access requires partner approval, app review, business verification, contact-sales, or a non-self-serve process.
- `unclear`: public evidence was insufficient or contradictory.

## API Breadth

Use this enum for practical integration surface:

- `none_or_unclear`: no public API found, or documentation is too ambiguous to classify.
- `narrow`: a small set of endpoints, usually one product area or a read-heavy API.
- `moderate`: several resource groups with useful read/write coverage.
- `broad`: many objects/actions across the app with meaningful automation potential.
- `platform_level`: large ecosystem API with admin, workflow, reporting, marketplace, extensions, or multi-product coverage.

## MCP Status

Separate existing MCP evidence from toolkit suitability:

- `official`: official MCP server or official MCP documentation exists.
- `community`: community MCP implementation found.
- `none_found`: no MCP found during research.
- `unclear`: evidence was ambiguous.

Important: `none_found` is not a buildability blocker by itself. A well-documented REST/GraphQL API can still be a strong toolkit candidate.

## Buildability Verdict

Use this enum for the practical Composio toolkit verdict:

- `buildable_now`: public docs, workable auth, and enough API breadth for useful agent actions.
- `buildable_with_caveats`: technically buildable, but with admin setup, plan limits, fragmented docs, or sandbox friction.
- `possible_but_gated`: API exists, but access is meaningfully blocked by sales, partner approval, app review, or business verification.
- `not_practical_today`: no usable public API, extremely limited API, or access is not realistically available without a partnership.
- `unclear_needs_review`: evidence is too weak or contradictory.

## Primary Blocker

Use one blocker per row for aggregation:

- `none`
- `partner_gated_access`
- `contact_sales_required`
- `paid_plan_required`
- `admin_setup_required`
- `no_public_api`
- `api_too_narrow`
- `poor_or_fragmented_docs`
- `no_sandbox_or_test_path`
- `app_review_or_business_verification`
- `unclear_access`
- `unknown`

## Opportunity Score

Score from 0-10:

- +2 public, official, well-structured developer docs
- +2 self-serve or low-friction credential path
- +2 broad enough action surface for agent tools
- +2 stable auth, webhooks, sandbox, or test path
- +2 low operational friction and few blockers

Suggested interpretation:

- 8-10: immediate build candidate
- 5-7: buildable with caveats or good candidate after targeted review
- 0-4: outreach-heavy, blocked, unclear, or low-leverage

## Confidence

Confidence should reflect evidence quality, not optimism.

High confidence:

- official docs found
- auth and API claims directly supported
- access/gating is explicitly documented
- buildability follows clearly from evidence

Medium confidence:

- official docs found, but access, sandbox, or breadth needs inference
- evidence supports most fields, with some gaps

Low confidence:

- missing official docs
- access model inferred from weak evidence
- contradictory docs
- buildability depends on assumptions

## Verification Strategy

Use a stratified sample of 15-20 apps:

- at least one or two apps per category
- mix of self-serve and gated rows
- include low-confidence rows
- include rows with enterprise, ads, fintech, or fragmented docs

For each sampled app, check:

- auth methods
- access model
- API protocol and breadth
- MCP status
- buildability verdict
- primary blocker

The final case study should show first-pass errors, corrections, and post-verification accuracy.

## Workflow Metadata

Stub records start with conservative workflow defaults:

- `research_status`: `pending`
- `verification.status`: `not_checked`
- `agent_confidence`: `low`
- `buildability_confidence`: `low`
- `human_review_required`: `unclear`
- `source_count`: `0`

Later modules should update these fields rather than overwriting the whole record blindly.

## Discovery Contract

`discover_sources.py` should only answer source-location questions:

- What is the official website?
- What is the official developer/docs portal?
- What is the best API reference or overview URL?
- What is the best auth documentation URL?
- What is the best pricing, access, app review, or credential-path URL?
- Is there an official or credible MCP source worth saving?

It must not classify auth, access model, API breadth, MCP status, or buildability. Those belong in extraction and verification.

Discovery stores shortcut URLs in `sources.*` and full provenance in `sources.discovered_sources`.

## Extraction Contract

`extract_record.py` consumes `app_records.discovered.jsonl` and produces `app_records.extracted.jsonl`.

It should fill first-pass fields from a compact source packet:

- `one_line_description`
- `auth_methods`
- `primary_auth_for_toolkit`
- `auth_complexity`
- `access`
- `api_surface`
- `mcp`
- `buildability`
- `evidence`
- `confidence`

It must not perform human correction or verifier-style contradiction analysis. Module 4 owns verification and confidence correction.

Default extraction is conservative: when source text has not been fetched, confidence is capped below `high`, even if discovered URL coverage is strong.

## Verification Contract

`verify_record.py` consumes `app_records.extracted.jsonl` and produces:

- `app_records.verified.jsonl`
- `verification_sample.jsonl`
- `verification_sample.csv`
- `verification_summary.json`

The verifier checks six field families:

- one-line description
- auth methods and primary auth
- access model
- API surface
- MCP status
- buildability verdict and blocker

Field-level outcomes:

- `correct`: the first-pass value is supported well enough by the available evidence.
- `partial`: directionally useful but incomplete, oversimplified, or missing nuance.
- `incorrect`: materially wrong or contradictory.
- `needs_review`: unresolved from the available evidence and should be manually checked.

Record-level statuses:

- `pass`: sampled and no material changes needed.
- `corrected`: sampled and one or more fields were changed.
- `flagged`: sampled and still needs manual review.
- `not_checked`: not part of the formal sample.

The current implementation is an automated verification scaffold. The final submission should clearly state which sampled rows received human review on top of this scaffold.

## Analysis Contract

`run_analysis.py` consumes `app_records.verified.jsonl` and `verification_summary.json`.

It computes:

- dataset summary
- buildability distribution
- access model distribution
- primary auth and all-auth distributions
- blocker counts
- category breakdown
- confidence distribution
- MCP distribution
- easy-win shortlist
- outreach-needed shortlist
- headline findings

## Visible Dataset Contract

`build_visible_dataset.py` consumes `app_records.verified.jsonl` and writes:

- `data/final/app_research_final.csv`
- `data/final/app_research_final.json`

This is the table-ready representation for the HTML case study. It intentionally flattens nested records into reviewer-friendly columns while preserving evidence URLs and verification status.

## Case Study Contract

`build_case_study.py` consumes:

- `data/analysis/analysis_summary.json`
- `data/final/app_research_final.json`
- `data/processed/verification_summary.json`

It renders `web/case_study.html` as a self-contained static page with embedded data for:

- hero metrics
- headline findings
- evaluation rubric
- agent workflow
- pattern charts
- easy-wins and outreach-needed queues
- verification/trustworthiness section
- searchable 100-app matrix
