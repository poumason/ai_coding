---
name: plugin-review
description: This skill should be used when the user asks to "review my plugin", "review my skill", "evaluate my plugin", "check plugin quality", "score my plugin", "validate my skill", "give me a quality report", "check if my plugin will pass review", "what score does my plugin get", "how to improve my plugin", or wants to know if a Claude Code plugin or skill meets quality standards. Also activate when the user points to a plugin directory and asks for feedback.
version: 1.0.0
---

# Plugin Review Skill

Perform a structured quality review of any Claude Code plugin or skill directory. Produce a scored report (0–100), declare PASS (≥ 80) or FAIL (< 80), and list prioritized improvements.

## Overview

Claude Code plugins follow a strict directory convention. Reviewing a plugin means checking:
1. Manifest correctness and naming
2. Component quality (skills, agents, commands)
3. Documentation completeness
4. Security hygiene

The output is always a **scored report** — not just a list of issues.

## Review Process

### Step 1 — Locate the Plugin Root

Identify the plugin root by finding the `.claude-plugin/plugin.json` manifest. If the user gives a path, start there. If none given, search the current working directory or ask the user.

```
plugin-root/
├── .claude-plugin/
│   └── plugin.json   ← required manifest
├── skills/
├── agents/
├── commands/
└── README.md
```

### Step 2 — Load the Scoring Rubric

Read `references/scoring-rubric.md` for the detailed scoring breakdown before running any checks. This ensures consistent point allocation.

### Step 3 — Run Dimension Checks

Run all five dimension checks in order. For each dimension, compute points earned vs. points available. Record deductions with specific file paths and line references.

**Dimension order:**
1. Structure & Manifest (25 pts)
2. Skills Quality (25 pts) — skip if no `skills/` directory
3. Agents Quality (20 pts) — skip if no `agents/` directory
4. Documentation (15 pts)
5. Security (15 pts)

When a dimension is skipped, redistribute its points proportionally across the remaining dimensions so the total stays 100. See `references/scoring-rubric.md` for redistribution math.

### Step 4 — Compute Total Score

Sum points earned across all active dimensions. Normalize to 100 using the formula in `references/scoring-rubric.md`.

### Step 5 — Determine Pass / Fail

- Score ≥ 80 → **PASS**
- Score < 80 → **FAIL** — list all issues that must be fixed to reach 80, ordered by point impact

### Step 6 — Generate Report

Produce the report using the template in `references/report-template.md`. Always include:
- Overall score and PASS/FAIL banner
- Per-dimension breakdown table
- Issues list with severity, point impact, file path, and fix guidance
- "How to reach 80" section (only on FAIL)
- Positive findings (what is done well)

## Severity Levels

| Severity | Definition |
|---|---|
| **Critical** | Instant structural failures — plugin cannot load |
| **Major** | Significant quality gaps causing large point deductions (≥ 5 pts each) |
| **Minor** | Small improvements with low point impact (< 5 pts each) |

## Instant Failure Conditions

The following automatically result in a score of 0 (skip all other checks):
- `.claude-plugin/plugin.json` does not exist
- `plugin.json` is invalid JSON
- `name` field missing from `plugin.json`
- No components present (no `skills/`, `agents/`, or `commands/`)

Report instant failures clearly before presenting a score.

## Writing Style for the Report

- Use imperative, direct language: "Add a `description` field" not "You should add..."
- Be specific: cite file paths, frontmatter fields, word counts
- Keep fix instructions concrete: one sentence minimum per issue
- Order issues by point impact (highest first)

## Additional Resources

### Reference Files

- **`references/scoring-rubric.md`** — Full per-dimension scoring breakdown with point tables
- **`references/report-template.md`** — Exact report format to produce
- **`references/review-criteria.md`** — Detailed criteria descriptions and examples for edge cases
