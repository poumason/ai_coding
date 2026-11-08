---
description: Review a Claude Code plugin or skill directory. Generates a scored report (0–100), declares PASS (≥ 80) or FAIL (< 80), and provides prioritized fix guidance.
argument-hint: <path-to-plugin-or-skill>
allowed-tools:
  ["Read", "Grep", "Glob", "Bash", "Agent"]
---

# Plugin Review Command

Review the Claude Code plugin or skill at the given path. If no path is provided, review the current working directory.

**Target path:** $ARGUMENTS

## Instructions

1. Determine the target path:
   - If `$ARGUMENTS` is provided, use that as the plugin root
   - If empty, use `.` (current directory)

2. Use the `plugin-reviewer` agent to perform the full review:
   - Pass the resolved target path to the agent
   - The agent will run all dimension checks, compute the score, and generate the report

3. Present the agent's report verbatim — do not summarize or truncate it.

4. After the report, if the result is FAIL, ask the user:
   > "Would you like me to fix the highest-impact issues now?"
   If yes, apply fixes in order of point impact, then re-run the review to confirm the new score.

## Examples

```
/review-plugin ./my-plugin
/review-plugin ../plugins/data-tools
/review-plugin
```
