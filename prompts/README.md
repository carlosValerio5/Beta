# prompts/

Versioned prompts for the product's AI agents. Behaviour docs live in
[`docs/agents/`](../docs/agents/README.md).

```
prompts/<agent>/v<N>.md
```

Each file is:

```markdown
---
name: beta_planner          # must match the directory
version: 1                  # must match the file name
model: claude-opus-5-5      # default model (overridable via BETA_*_MODEL)
effort: high                # output_config.effort
max_tokens: 16000
---
<system prompt — stable, cached>
=== user ===
<user template with $variables (string.Template)>
```

Rules:

1. **Never edit a released version.** Copy to `v(N+1).md`, change it, run `make eval`, and compare
   against the previous version's report before switching the default.
2. The registry loads the highest version unless code pins one; every LLM call records
   `name@vN` and the model in provenance, so bronze always says which prompt produced what.
3. Keep the system prompt free of per-request data so prompt caching keeps working.
4. Output format is enforced by structured outputs (JSON schema from the Pydantic draft model) —
   prompts describe *what good looks like*, not JSON syntax.
