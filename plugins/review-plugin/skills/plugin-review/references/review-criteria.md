# Review Criteria — Detailed Edge Cases

## Structure & Manifest

### Kebab-case Validation

A valid plugin name:
- All lowercase
- Only letters, digits, and hyphens
- No spaces, underscores, or special characters
- Examples that pass: `my-plugin`, `code-review`, `api-tools-v2`
- Examples that fail: `MyPlugin`, `my_plugin`, `my plugin`, `my.plugin`

### Semver Validation

Valid version strings: `1.0.0`, `0.1.0`, `2.3.14`, `1.0.0-beta`
Invalid: `1.0`, `v1.0.0`, `latest`, `1`

### Manifest Location

The manifest MUST be at `.claude-plugin/plugin.json` relative to plugin root. These are wrong:
- `plugin.json` (at root without `.claude-plugin/`)
- `.claude-plugin/manifest.json`
- `config/plugin.json`

---

## Skills Quality Edge Cases

### Trigger Phrase Quality

**Strong triggers** (full points):
```yaml
description: This skill should be used when the user asks to "create a hook",
  "add a PreToolUse hook", "set up event handlers", or mentions hook events
  (PreToolUse, PostToolUse, Stop, SubagentStop).
```

**Weak triggers** (partial points — -2 pts each):
- Generic phrasing: "when working with hooks"
- No quoted phrases: "for hook-related tasks"
- Wrong person: "Use this skill when you need hooks"

### Progressive Disclosure

Count words in the SKILL.md body (excluding frontmatter). Apply deductions:

| Word Count | Deduction |
|---|---|
| ≤ 2,000 | 0 (ideal) |
| 2,001 – 3,000 | 0 (acceptable) |
| 3,001 – 4,000 | -1 pt |
| 4,001 – 5,000 | -1 pt |
| > 5,000 | -2 pts |

A SKILL.md over 5,000 words strongly suggests content that belongs in `references/`.

### Broken File References

For each path referenced in a SKILL.md body (e.g., `` **`references/patterns.md`** ``), verify the file exists.
- Each broken reference: -1 pt (up to -2 pts max per skill)

---

## Agents Quality Edge Cases

### Example Block Format

A valid `<example>` block must contain:
```
<example>
Context: [Situation description]
user: "[User query]"
assistant: "[Response]"
<commentary>
[Why this triggers the agent]
</commentary>
</example>
```

Partial credit (-1 pt each):
- Example block exists but missing `<commentary>`
- Example block exists but user/assistant not separated

### System Prompt Length

Minimum: 100 characters (anything shorter likely isn't useful)
Recommended: 500+ characters for a meaningful role definition
Deduction: -2 pts if < 100 chars, -1 pt if 100-200 chars

---

## Documentation Edge Cases

### README Completeness

Check for the following sections (case-insensitive heading match):

| Section | Points |
|---|---|
| Purpose / Overview / Description | 1 |
| Features | 0.5 |
| Usage / How to use | 1 |
| Installation | 1 |
| Any code block examples | 0.5 |

### License

Accepted LICENSE file names: `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `license`, `LICENCE`

---

## Security Edge Cases

### Secret Detection Patterns

Scan all non-binary files for these patterns (case-insensitive):
- `api_key\s*[=:]\s*[^<{]` (followed by a non-placeholder)
- `password\s*[=:]\s*[^<{]`
- `secret\s*[=:]\s*[^<{]`
- `token\s*[=:]\s*[^<{]`
- `private_key\s*[=:]\s*[^<{]`
- `aws_access_key_id\s*[=:]`
- `-----BEGIN RSA PRIVATE KEY-----`

**False positives to ignore:**
- Values that are placeholders: `<YOUR_API_KEY>`, `YOUR_TOKEN_HERE`, `xxx`, `...`, `$ENV_VAR`
- Comments describing what a field should contain (not actual values)
- Test files with obviously fake credentials (e.g., `password=test123` in `tests/`)

### Path Safety

Scan `hooks/hooks.json` and `.mcp.json` for hardcoded absolute paths. A path is unsafe if it:
- Starts with `/Users/`, `/home/`, `C:\`, etc.
- Does not use `${CLAUDE_PLUGIN_ROOT}`

Each unsafe path found: -1 pt (up to -3 pts max).

---

## Instant Failure Conditions Summary

| Condition | How to Detect |
|---|---|
| `.claude-plugin/plugin.json` missing | File does not exist at that path |
| `plugin.json` invalid JSON | Parse fails |
| `name` field missing | Key not present in JSON |
| No components present | `skills/`, `agents/`, `commands/` all absent or empty |

On instant failure: report score = 0, FAIL, and describe the specific condition. Do not run other checks.
