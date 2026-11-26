# AI Brief Daily: Report Style Guide

This is the spec every daily report must follow, whether it's written by the Grok Bot routine (main path) or by the n8n workflow (optional). If it's not in this file, it's not part of the format.

## 1. File

- Path: `content/reports/YYYY-MM-DD.md` (date in **Africa/Casablanca**, the morning of publication).
- One report per day. If the file already exists, overwrite it instead of creating a second one.
- UTF-8, LF line endings, no raw HTML (Goldmark `unsafe = false` strips it).

## 2. Front matter (YAML, exact keys)

```yaml
---
title: "AI Brief — Nov 26, 2026: <3 biggest stories, ≤ 110 chars total>"
date: 2026-11-26T07:00:00+00:00        # ISO 8601 with offset; Casablanca is +00:00 / +01:00 during summer time
lastmod: 2026-11-26T07:00:00+00:00
description: "<140–160 char SEO summary naming the top 3–4 stories>"
summary: "<1 sentence, ≤ 200 chars, shown on list pages>"
tags: ["OpenAI", "Anthropic", "AI agents"]   # 5–10, Title Case for orgs/products, reuse existing tags
categories: ["Daily Report"]                 # always exactly this
keywords: ["<3–6 search phrases>"]
ShowToc: true
TocOpen: false
draft: false
---
```

Rules: `date` must not be in the future at build time (Hugo skips future posts). Quote every string. No trailing commas.

## 3. Body: section order (H2 headings, exact text)

1. `## TL;DR`: 4–6 bullets, one per story, **bold the actor** and keep each bullet to one sentence with the key number or date.
2. `## Top stories`: 4–6 stories, ranked by importance. Each story:
   ```markdown
   ### N. <Plain headline, no clickbait>

   **What happened.** 2–4 sentences: who, what, when, key numbers. Facts only, all from the sources.

   **Why it matters.** 2–4 sentences: impact for builders, businesses or users, including any caveat.

   **Sources:** [Publisher](url) · [Publisher](url)
   ```
3. `## Deep dive: <theme>`: 300–500 words on the single most consequential story or a trend that links several stories. Suggested structure: context → what changes (numbered list) → the catch → "What to do now".
4. `## Sources`: full list, `- Publisher — [Title](url) (Mon D, YYYY)`.
5. Closing italic line: `*This report was drafted with AI assistance from the sources above and reviewed for accuracy. Figures are as reported by the cited sources.*`

## 4. Story selection

- Only news from the **last 24–36 hours**. Older items are allowed only as context.
- Priority: frontier model/product launches > major research results > policy/regulation/export controls > big funding/M&A (≥ $100M) > notable open-source releases > robotics/hardware.
- Mix it up: no more than 2 stories about the same company.
- Skip: rumors with no primary or reputable source, pure stock-price moves, listicles, sponsored posts.

## 5. Sourcing & accuracy

- Every story needs **≥ 1 primary source** (company blog, paper, filing, official docs) when one exists, plus up to 2 reputable secondary sources.
- Never invent numbers, quotes, dates or URLs. If a figure isn't in a source, leave it out.
- Label claims as claims ("OpenAI says…") when only the company reports them.
- Link to canonical URLs (no tracking params, no Google AMP).

## 6. Voice

- Plain English, short sentences, active voice. Explain jargon on first use.
- Neutral and skeptical: no hype words ("revolutionary", "game-changing", "insane").
- Readers are developers, founders and operators, so make "why it matters" practical.
- Length: 1,200–2,000 words total.

## 7. Publishing checklist

- [ ] Filename date = front matter date (Casablanca)
- [ ] 4–6 stories, each with What happened / Why it matters / Sources
- [ ] All links resolve; no raw HTML
- [ ] `hugo --minify` builds with no errors
- [ ] Commit message: `report: YYYY-MM-DD`, pushed to `main` (this triggers the Pages deploy)

Reference example: `content/reports/2026-11-26.md`.
