# Scoring Rubric — review-plugin

## Pass / Fail Threshold

| Result | Condition |
|---|---|
| **PASS** | Total score ≥ 80 |
| **FAIL** | Total score < 80 |

---

## Dimension Weights (Default)

| # | Dimension | Max Points |
|---|---|---|
| 1 | Structure & Manifest | 25 |
| 2 | Skills Quality | 25 |
| 3 | Agents Quality | 20 |
| 4 | Documentation | 15 |
| 5 | Security | 15 |
| | **Total** | **100** |

---

## Point Redistribution (When Dimensions Are Skipped)

When a plugin has no `skills/` directory, Dimension 2 is skipped and its 25 points are
redistributed to the remaining dimensions proportionally:

```
remaining_total = 100 - skipped_points
scale_factor = 100 / remaining_total
each_dimension_max = original_max * scale_factor  (round to nearest integer)
```

Example — plugin with no agents (Dimension 3 skipped, 20 pts removed):
- Remaining base: 80 pts → scale factor = 100/80 = 1.25
- Structure: 25 × 1.25 = 31 pts
- Skills: 25 × 1.25 = 31 pts
- Documentation: 15 × 1.25 = 19 pts
- Security: 15 × 1.25 = 19 pts

Apply rounding so the total equals exactly 100.

---

## Dimension 1 — Structure & Manifest (25 pts)

### 1.1 Manifest Existence (8 pts)

| Check | Points |
|---|---|
| `.claude-plugin/plugin.json` file exists | 5 |
| `plugin.json` is valid JSON (parseable) | 3 |

**If `.claude-plugin/plugin.json` is missing or invalid JSON → INSTANT FAILURE (score = 0)**

### 1.2 Manifest Content (10 pts)

| Check | Points |
|---|---|
| `name` field present | 4 |
| `name` is kebab-case (lowercase, hyphens only, no spaces) | 2 |
| `version` field present and follows semver (X.Y.Z) | 2 |
| `description` field present and non-empty | 2 |

**If `name` field missing → INSTANT FAILURE (score = 0)**

### 1.3 Directory Structure (7 pts)

| Check | Points |
|---|---|
| At least one component directory present (`skills/`, `agents/`, or `commands/`) | 4 |
| No component directories nested inside `.claude-plugin/` | 2 |
| File/directory names use kebab-case | 1 |

**If no components present → INSTANT FAILURE (score = 0)**

---

## Dimension 2 — Skills Quality (25 pts)

*Skip this dimension entirely if `skills/` directory does not exist.*

Evaluate all skills found under `skills/*/SKILL.md`. Score the **average** across all skills.

### 2.1 Frontmatter Validity (8 pts per skill, averaged)

| Check | Points |
|---|---|
| `SKILL.md` file exists in skill directory | 3 |
| YAML frontmatter present (starts/ends with `---`) | 2 |
| `name` field in frontmatter | 1 |
| `description` field in frontmatter | 2 |

### 2.2 Description Quality (10 pts per skill, averaged)

| Check | Points |
|---|---|
| Description uses third person: "This skill should be used when..." | 3 |
| Description includes specific trigger phrases (quoted user queries) | 4 |
| Description is specific, not vague | 3 |

**Trigger phrase examples that pass:**
```yaml
description: This skill should be used when the user asks to "create a hook", "add a PreToolUse hook"...
```

**Trigger phrase examples that fail:**
```yaml
description: Use this when working with hooks.  # wrong person, vague, no phrases
```

### 2.3 Content Quality (7 pts per skill, averaged)

| Check | Points |
|---|---|
| SKILL.md body uses imperative/infinitive form (not "you should...") | 3 |
| SKILL.md body is ≤ 3,000 words (lean, progressive disclosure) | 2 |
| Referenced files (references/, examples/, scripts/) actually exist | 2 |

---

## Dimension 3 — Agents Quality (20 pts)

*Skip this dimension entirely if `agents/` directory does not exist.*

Evaluate all agent files found under `agents/**/*.md`. Score the **average** across all agents.

### 3.1 Frontmatter Completeness (10 pts per agent, averaged)

| Check | Points |
|---|---|
| YAML frontmatter present | 2 |
| `name` field present (kebab-case, 3-50 chars) | 2 |
| `description` field present | 2 |
| `model` field present and valid (`inherit`, `sonnet`, `opus`, `haiku`) | 2 |
| `color` field present and valid (`blue`, `cyan`, `green`, `yellow`, `magenta`, `red`) | 1 |
| `tools` field present (array) | 1 |

### 3.2 Description & Examples (6 pts per agent, averaged)

| Check | Points |
|---|---|
| Description includes at least one `<example>` block | 3 |
| Example blocks contain `context`, `user`, `assistant`, and `<commentary>` | 3 |

### 3.3 System Prompt Quality (4 pts per agent, averaged)

| Check | Points |
|---|---|
| System prompt body exists and is > 100 characters | 2 |
| System prompt is specific to the agent's role (not generic) | 2 |

---

## Dimension 4 — Documentation (15 pts)

### 4.1 README (10 pts)

| Check | Points |
|---|---|
| `README.md` exists at plugin root | 4 |
| README describes plugin purpose | 2 |
| README has usage instructions (commands, invocation) | 2 |
| README has installation instructions | 2 |

### 4.2 Supplementary Docs (5 pts)

| Check | Points |
|---|---|
| `LICENSE` file present | 2 |
| No TODO/FIXME/placeholder comments left in component files | 2 |
| No broken internal file references in SKILL.md files | 1 |

---

## Dimension 5 — Security (15 pts)

### 5.1 Secrets & Credentials (10 pts)

| Check | Points |
|---|---|
| No hardcoded API keys, tokens, passwords in any file | 5 |
| No `.env` files committed with real secrets | 3 |
| No secrets in example files | 2 |

Patterns that trigger deductions: `api_key=`, `password=`, `secret=`, `token=` followed by a non-placeholder value (i.e., not `<YOUR_KEY>`, `YOUR_TOKEN`, `xxx`).

### 5.2 Path Safety (5 pts)

| Check | Points |
|---|---|
| Hook and MCP commands use `${CLAUDE_PLUGIN_ROOT}` instead of hardcoded paths | 3 |
| No absolute paths outside of `${CLAUDE_PLUGIN_ROOT}` in hook scripts | 2 |

---

## Score Computation Example

Plugin has `skills/` and `agents/` and `commands/`, full dimensions active:

| Dimension | Available | Earned |
|---|---|---|
| Structure & Manifest | 25 | 22 |
| Skills Quality | 25 | 18 |
| Agents Quality | 20 | 16 |
| Documentation | 15 | 10 |
| Security | 15 | 15 |
| **Total** | **100** | **81** → **PASS** |
