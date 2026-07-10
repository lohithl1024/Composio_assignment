# Composio Analyzer — Agentic Integration Research Pipeline

A research pipeline built for Composio’s AI Product Ops Intern take-home assignment.

**Goal:** analyze a set of 100 requested apps and determine whether each app is realistically buildable as a Composio toolkit today — based on auth model, access friction, API surface, MCP evidence, and practical buildability.

This project does **not** just generate a spreadsheet. It treats the assignment as an **agentic product-ops workflow**:

- gather official sources for each app
- extract structured integration facts
- verify a sample instead of trusting the first pass blindly
- surface patterns across the 100-app set
- render the results into a clean reviewer-facing case study site

---

# Live deliverable

- **Case study / site:** https://composio-assignment-pi.vercel.app/
- **Repository:** Composio_assignment

---

# What this project answers

For each app in the 100-app research set, the pipeline attempts to answer:

- What category is it in?
- What does it do in one line?
- What auth method does it use?
- Is access self-serve, paid-plan gated, admin/workspace dependent, or partner-gated?
- How broad is the API surface?
- Is there MCP evidence or a known MCP server?
- Could Composio build a toolkit for it today?
- If not, what is the main blocker?
- What evidence supports the answer?

The output is then aggregated to answer the more important product-ops questions:

- Which categories are easiest to operationalize first?
- Where does access friction matter more than API existence?
- Which apps are “easy wins” vs outreach-heavy?
- Where is the automation trustworthy, and where should human QA stay in the loop?

---

# Project structure

```bash
integration-radar/
├─ data/
│  ├─ input/
│  │  └─ apps.csv
│  ├─ processed/
│  │  ├─ app_records.stub.jsonl
│  │  ├─ app_records.discovered.jsonl
│  │  ├─ app_records.extracted.jsonl
│  │  ├─ app_records.verified.jsonl
│  │  ├─ verification_sample.jsonl
│  │  ├─ verification_sample.csv
│  │  └─ verification_summary.json
│  ├─ analysis/
│  │  ├─ analysis_summary.json
│  │  ├─ category_breakdown.csv
│  │  ├─ buildability_distribution.csv
│  │  ├─ access_distribution.csv
│  │  ├─ auth_distribution.csv
│  │  ├─ all_auth_distribution.csv
│  │  ├─ blocker_counts.csv
│  │  ├─ easy_wins.csv
│  │  └─ outreach_needed.csv
│  └─ final/
│     ├─ app_research_final.csv
│     └─ app_research_final.json
│
├─ docs/
│  └─ schema_and_rubrics.md
│
├─ src/
│  ├─ bootstrap_records.py
│  ├─ discover_sources.py
│  ├─ extract_record.py
│  ├─ verify_record.py
│  ├─ run_analysis.py
│  ├─ build_visible_dataset.py
│  ├─ build_case_study.py
│  ├─ source_packet.py
│  ├─ prompts/
│  │  └─ extraction_prompt.md
│  └─ models/
│     ├─ app_record.py
│     ├─ verification.py
│     └─ ...
│
└─ web/
   ├─ index.html / case study pages
   └─ templates/
      └─ case_study.html.j2
