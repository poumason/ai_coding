# model-profile

A Claude Code mod that lets you switch between named model configuration
profiles (for example a "cloud" profile pointing at Anthropic's own API, and
an "internal" profile pointing at a company gateway) with a single slash
command instead of hand-editing `~/.claude/settings.json` every time.

## Setup

On first load the mod creates `~/.claude/profiles/` with two sample files,
`cloud.json` and `internal.json`. Edit them with the real values for each
environment, for example:

```json
{
  "ANTHROPIC_BASE_URL": "https://internal-gateway.example.com",
  "ANTHROPIC_AUTH_TOKEN": "...",
  "ANTHROPIC_MODEL": "internal-model-id"
}
```

Add as many `<name>.json` files as you need; the file name (without `.json`)
is the profile's name.

## Usage

- `/profile` or `/profile list` — list known profiles, marking the one that
  matches the current settings.
- `/profile <name>` — apply that profile: it tries to set the variables live
  on the running process, and always writes them into
  `~/.claude/settings.json` (backing up the previous file as `.bak`) so the
  change survives a restart.

`ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` are normally read once when
`claude` starts, so if replies still look like the old provider after
switching, exit (Ctrl+D or `/exit`) and run `claude` again — the saved
settings.json will take effect on the fresh start.

## Installation

Copy or symlink this plugin into your project:

```bash
cp -r model-profile /path/to/project/.claude-plugin/
```

Or reference it with `--plugin-dir`:

```bash
claude --plugin-dir /path/to/model-profile
```
