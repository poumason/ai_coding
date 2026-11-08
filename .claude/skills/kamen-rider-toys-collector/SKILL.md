---
name: kamen-rider-toys-collector
description: Scrape Kamen Rider toy news from hacchaka.net and tamashiiweb.com using Playwright MCP, then produce a styled HTML summary of upcoming and recently released figures (S.H.Figuarts, FRS, and other types) with release dates and links. Use this skill whenever the user says "give me news of kamen rider", "kamen rider toy news", "what's new in kamen rider figures", "check hacchaka", "check tamashii", or any variation asking about Kamen Rider collectibles, figures, or toy releases.
---

## Goal

Visit the two primary Kamen Rider toy news sources, extract all toy announcements and release information, translate everything to English, and write a single HTML file the user can open in their browser.

## Sources

| Site | URL | Notes |
|------|-----|-------|
| Hacchaka | https://hacchaka.net/ | Japanese hobby news blog; covers SHF, FRS, pre-orders |
| Tamashii Web | https://tamashiiweb.com/ | Bandai's official Tamashii Nations site; use the English version if available |

You may add more sources in future iterations — just follow the same pattern below.

## Step-by-step workflow

### 1. Navigate and scrape each site

Use `mcp__playwright__browser_navigate` to open each URL, then `mcp__playwright__browser_snapshot` to read the page content.

For **hacchaka.net**:
- Navigate to `https://hacchaka.net/`
- Take a snapshot and look for posts/articles mentioning Kamen Rider
- Click into individual article links to get release dates, prices, and product names
- Focus on the most recent 10–15 articles

For **tamashiiweb.com**:
- Navigate to `https://tamashiiweb.com/`
- Look for a "New Items", "Coming Soon", or "Kamen Rider" section
- Extract product names, categories, release dates, and prices
- If the site has a search or filter for "仮面ライダー" (Kamen Rider), use it

### 2. Identify toy types

Categorize each item you find into one of these types (or "Other" if none match):

- **S.H.Figuarts (SHF)** — Bandai's premium articulated figure line
- **FRS (Figure-rise Standard)** — plastic model kit line
- **Chogokin / DX** — die-cast or electronic roleplay toys
- **Converge / Candy Toy** — small blind-box style figures
- **Other** — anything else (statues, plush, etc.)

### 3. Translate to English

All product names, descriptions, and notes should be in English. Use these conventions:
- Keep the original Japanese name in parentheses when the official English name is unclear, e.g. "Kamen Rider Geats (仮面ライダーギーツ)"
- Dates: convert Japanese date formats (令和7年 / 2025年) to `YYYY-MM-DD` or `Month YYYY`
- Prices: keep yen (¥) with the original amount

### 4. Generate the HTML summary

Write the output to `~/kamen_rider_news.html` (or the current working directory if home is unavailable).

The HTML file must:
- Have a clean, readable layout styled with inline CSS (dark background preferred — collectors browse at night)
- Show a **last updated** timestamp at the top
- Have a **source legend** linking to hacchaka.net and tamashiiweb.com
- Group items into two sections: **Upcoming / Pre-order** and **Recently Released**
- For each item, show:
  - Product name (translated, with Japanese in parentheses if needed)
  - Type badge (SHF / FRS / etc.)
  - Release / shipping date
  - Price (if available)
  - A clickable link back to the source article
- If a release date is unknown, show "TBA"

### HTML template structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Kamen Rider Toy News</title>
  <style>
    body { background: #1a1a2e; color: #eee; font-family: sans-serif; padding: 2rem; }
    h1 { color: #e94560; }
    .badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-right:6px; }
    .shf   { background:#0f3460; color:#a8d8ea; }
    .frs   { background:#533483; color:#e2cfff; }
    .other { background:#444; color:#ccc; }
    .item  { border:1px solid #333; border-radius:6px; padding:1rem; margin:0.75rem 0; }
    .item a { color:#e94560; text-decoration:none; }
    .item a:hover { text-decoration:underline; }
    .date  { color:#aaa; font-size:0.9em; }
    .price { color:#f5a623; font-size:0.9em; margin-left:8px; }
    h2 { border-bottom:1px solid #e94560; padding-bottom:4px; margin-top:2rem; }
    .sources { font-size:0.85em; color:#888; margin-bottom:2rem; }
    .sources a { color:#aaa; }
  </style>
</head>
<body>
  <h1>🦾 Kamen Rider Toy News</h1>
  <div class="sources">
    Last updated: [TIMESTAMP] &nbsp;|&nbsp;
    Sources: <a href="https://hacchaka.net/" target="_blank">Hacchaka</a>,
    <a href="https://tamashiiweb.com/" target="_blank">Tamashii Web</a>
  </div>

  <h2>📦 Upcoming / Pre-order</h2>
  <!-- items here -->

  <h2>✅ Recently Released</h2>
  <!-- items here -->

</body>
</html>
```

Each item block:
```html
<div class="item">
  <span class="badge shf">SHF</span>
  <strong><a href="[SOURCE URL]" target="_blank">[Product Name]</a></strong>
  <br>
  <span class="date">📅 [Release Date]</span>
  <span class="price">¥[Price]</span>
</div>
```

Use badge class `shf`, `frs`, or `other` depending on the type.

### 5. Open the file

After writing the HTML, tell the user the file path and offer to open it with:
```bash
open ~/kamen_rider_news.html
```

## Notes

- If a site is slow or requires scrolling to load more content, use `mcp__playwright__browser_snapshot` after waiting a moment
- If JavaScript heavy content doesn't load, try `mcp__playwright__browser_wait_for` with a few seconds
- Hacchaka is in Japanese — read the snapshot carefully and translate methodically
- If you find fewer than 5 items total, mention it and suggest the user check the sites manually for any login-gated content
- When adding new sources in the future, add them to the Sources table above and follow the same scrape → translate → categorize pattern
