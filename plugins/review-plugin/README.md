# review-plugin

Automated quality review tool for Claude Code skills and plugins. Generates a scored report (0-100), marks the plugin as **PASS** (≥ 80) or **FAIL** (< 80), and provides prioritized improvement guidance.

## Features

- Scores plugins across five dimensions: Structure, Skills, Agents, Documentation, and Security
- Pass/fail threshold: **80 / 100**
- Identifies critical blockers vs. minor improvements
- Provides concrete, actionable fix guidance for every deduction

## Usage

### Auto-activation (Skill)

The `plugin-review` skill activates automatically when you ask Claude to review a plugin or skill:

> "Review my plugin at ./my-plugin"
> "Check my skill quality"
> "Evaluate this plugin and tell me what to fix"

### Slash command

```
/review-plugin <path-to-plugin>
```

Example:
```
/review-plugin ./my-awesome-plugin
```

### Direct agent invocation

Ask the `plugin-reviewer` agent directly:

> "Use the plugin-reviewer agent to review ./my-plugin and give me a full report"

## Scoring Rubric

| Category | Points | What is checked |
|---|---|---|
| Structure & Manifest | 25 | `plugin.json` validity, kebab-case name, semver version, directory layout |
| Skills Quality | 25 | SKILL.md frontmatter, trigger phrases, progressive disclosure, writing style |
| Agents Quality | 20 | Frontmatter completeness, `<example>` blocks, system prompt quality |
| Documentation | 15 | README completeness, LICENSE, clear usage instructions |
| Security | 15 | No hardcoded secrets, HTTPS where applicable, safe `${CLAUDE_PLUGIN_ROOT}` usage |

> Categories with no applicable components are skipped and points redistributed proportionally so the total always equals 100.

## Pass / Fail

- **PASS** — score ≥ 80
- **FAIL** — score < 80 (report lists exactly what must be fixed to reach 80)

## Installation

Copy or symlink this plugin into your project:

```bash
cp -r review-plugin /path/to/project/.claude-plugin/
```

Or reference it with `--plugin-dir`:

```bash
cc --plugin-dir /path/to/review-plugin
```
