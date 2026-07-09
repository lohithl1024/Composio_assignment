# Extraction Prompt

You are extracting Composio toolkit readiness data from a compact research packet.

Use only the supplied packet and the rubric values. If the packet does not support a claim, mark it as unclear and lower confidence. Do not browse the web inside this step.

Return normalized JSON that can be merged into `AppResearchRecord`.

Required outputs:

- `one_line_description`
- `auth_methods`
- `primary_auth_for_toolkit`
- `auth_complexity`
- `auth_notes`
- `access`
- `api_surface`
- `mcp`
- `buildability`
- `evidence`
- `confidence`

Evidence is required for at least:

- description
- auth methods
- access model
- API surface
- buildability verdict

Separate existing MCP evidence from MCP/toolkit suitability.
