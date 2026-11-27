# AI Brief Daily

An auto-publishing AI news site: **a daily deep report → Hugo → GitHub Actions → GitHub Pages**.

Every morning (~07:00 Africa/Casablanca) a new report lands in `content/reports/YYYY-MM-DD.md` on `main`. That push triggers `.github/workflows/deploy.yml`, which builds the site with Hugo and deploys it to GitHub Pages. No server to run.

```
Report writer ──commit content/reports/YYYY-MM-DD.md──▶ main ──▶ GitHub Actions (hugo --minify) ──▶ GitHub Pages
  ├─ A) Grok Bot routine   (main path: researches the news itself, then scripts/publish-report.sh)
  └─ B) n8n workflow       (optional: RSS → LLM → GitHub Contents API)
```

## What's in the repo

| Path | What it does |
|---|---|
| `hugo.toml` | Site config: name, SEO, menus, monetization settings (empty = hidden on the public site). **Rename the site here** (`title`, `params.homeInfoParams`, `params.author`, `copyright`). |
| `themes/PaperMod/` | [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme. CI checks it out from upstream pinned to commit `1181196`; it is not stored in this repo (gitignored). Fast, no JS framework, dark/light modes, search, OpenGraph/Twitter/schema.org built in. |
| `content/reports/` | Daily deep reports. `2026-11-26.md` is a real sample. |
| `docs/report-style.md` | **The report spec**: front matter, section order, sourcing rules, voice, checklist. Both writers follow it. |
| `scripts/publish-report.sh` | Validates a report, build-checks it, then commits and pushes it to `main`. |
| `layouts/_partials/extend_head.html` | AdSense loader (only when configured). |
| `layouts/_partials/extend_post_content.html` | Under each report: in-article ad slot, newsletter form, sponsor block, affiliate list. |
| `layouts/_partials/get_cover.html`, `cover.html`, `templates/` | Heading images and Open Graph / Twitter share tags. |
| `assets/images/cover-base.png` | Branded 1200×630 base used to generate a cover when a report has no custom image. |
| `assets/fonts/` | Inter (SIL Open Font License) used to paint the title and date on auto covers. |
| `assets/css/extended/monetize.css` | Styling for those blocks. |
| `.github/workflows/deploy.yml` | Build and deploy to Pages on every push to `main`. |
| `n8n/ai-brief-workflow.json` | Importable n8n workflow (option B). |
| `n8n/build_workflow.py` | Regenerates the workflow JSON, e.g. after editing feeds, the prompt or `docs/report-style.md`. |

Built in: RSS (`/index.xml`, plus one feed per section and tag), `sitemap.xml`, `robots.txt`, tags and categories, archive, search, reading time, share buttons, and clean permalinks (`/reports/2026/11/26/`).


## Cover images

Reports get a heading image (and matching `og:image` / `twitter:image`) automatically: Hugo paints the title and date onto `assets/images/cover-base.png` at build time. No front matter is required. To use your own image, add it under `static/images/` or `assets/images/` (no leading slash, so the `/ai-brief-site/` subpath stays intact) and set:

```yaml
cover:
  image: "images/my-cover.png"
  alt: "Short description"
  caption: "Optional caption, shown on the report page only"
  relative: false   # true if the file lives in the report's page bundle
  hidden: false     # hides it on the post and in lists; share tags still use it
```

## Setup

### 1. Create the GitHub repo
1. Create an empty repo, e.g. `t-el/ai-brief-site` (public, so Pages is free).
2. Push this folder:
   ```bash
   git remote add origin git@github.com:t-el/ai-brief-site.git
   git push -u origin main
   ```
3. **Settings → Pages → Build and deployment → Source: _GitHub Actions_.**
4. Go to the **Actions** tab, wait for "Deploy Hugo site to GitHub Pages" to finish (or re-run it), and the site goes live at `https://t-el.github.io/ai-brief-site/`. You don't need to edit `baseURL`: CI injects it from `actions/configure-pages`.

### 2A. Daily writer: Grok Bot routine (main path)
A scheduled routine researches the last 24h of AI news on the web, writes the report following **`docs/report-style.md`**, saves it, and publishes it:
```bash
scripts/publish-report.sh /path/to/draft.md            # date defaults to today (Africa/Casablanca)
scripts/publish-report.sh draft.md 2026-11-27          # explicit date
NO_PUSH=1 scripts/publish-report.sh draft.md           # commit only, don't push
```
The script checks the front matter and the required sections, refuses `draft: true`, runs `hugo --minify`, commits `report: YYYY-MM-DD`, then rebases and pushes to `main`.
It needs push access from wherever it runs (SSH deploy key with write access, or an HTTPS remote using a fine-grained token, see below).

### 2B. Daily writer: n8n workflow (optional alternative)
Works on n8n Cloud or self-hosted.
1. **Workflows → Import from File →** `n8n/ai-brief-workflow.json`.
2. Create two **Header Auth** credentials:
   - **LLM API key**: Name `Authorization`, Value `Bearer <your key>`. Works with any OpenAI-compatible API (OpenAI, OpenRouter, Groq, xAI, DeepSeek, Together, a local Ollama/vLLM…).
   - **GitHub token**: Name `Authorization`, Value `Bearer github_pat_…` (see the token section below).
3. Open the nodes **LLM: Write Deep Report**, **GitHub: Get Existing File SHA** and **GitHub: Commit Report to main**, and select the matching credential (the JSON only holds placeholder IDs).
4. In the **Config** node, set `llmBaseUrl`, `model`, `githubOwner`, `githubRepo` and `githubBranch`. You can also tune `lookbackHours`, `maxItems` and `systemPrompt`.
5. Click **Execute workflow** once to test, then toggle it **Active**. The schedule is `0 7 * * *`, and the workflow timezone is set to Africa/Casablanca.

Flow: *Schedule → Config → RSS feed list → Read RSS (one request per feed, failures skipped) → Merge/dedupe the last 24h, build the prompt → LLM → Validate format and base64-encode → GitHub GET (sha if the file exists) → GitHub PUT `content/reports/YYYY-MM-DD.md` on main → Actions deploys.*

Default feeds: OpenAI News, Google DeepMind, Google AI (Keyword), Hugging Face, TechCrunch AI, The Verge AI, MIT Technology Review AI, Hacker News (AI, 100+ points, via hnrss.org) and arXiv cs.AI (capped at 5). Anthropic has no official RSS feed, so its news usually comes in through TechCrunch, The Verge and HN. Some feeds block datacenter IPs or rate-limit from time to time (TechCrunch returned 403 from a test server). The workflow just skips any feed that fails. If fewer than 4 fresh items are found, it stops without publishing.

### 3. Fine-grained GitHub token (for n8n or HTTPS pushes)
GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate:
- **Repository access:** *Only select repositories* → `ai-brief-site`
- **Permissions:** *Contents: Read and write* (Metadata: read is added automatically). Nothing else.
- Expiration: 90 days–1 year. Set a reminder to rotate it.

### 4. Custom domain (optional)
1. Buy a domain and add a `CNAME` DNS record pointing at `t-el.github.io` (or A records for an apex domain).
2. **Settings → Pages → Custom domain**, then tick **Enforce HTTPS**.
3. `configure-pages` picks up the new base URL automatically. Optionally also update `baseURL` in `hugo.toml` for local builds.

### Local development
```bash
git clone https://github.com/adityatelange/hugo-PaperMod themes/PaperMod   # once; CI pins commit 1181196
hugo server -D          # http://localhost:1313
hugo --minify           # production build into ./public
```

## Monetization notes

Settings live in `[params.monetization]` in `hugo.toml`. **The public site renders a block only when that field is actually filled in.** Leave a value empty and that block outputs nothing — no “coming soon”, no config snippets, no example links. The contact page for sponsorships is `/advertise/` (`content/advertise.md`).

1. **Newsletter first** (the biggest long-term asset). Create a free list on Beehiiv, Buttondown, ConvertKit or MailerLite and paste the form action URL into `newsletterAction` (and optionally `newsletterCTA`). Beehiiv also has a built-in ad network and a referral program. Republish each report as the daily email.
2. **Sponsorships.** Once you have a real offer, set `sponsorText` and `sponsorURL` (usually `/advertise/`). Until both are set, no sponsor box appears under reports. The Advertise page itself is always public and points to `elkarroumytaha@gmail.com`.
3. **Affiliates.** Add real referral links as `[[params.monetization.affiliates]]` entries (`name`, `url`, `blurb`). They're marked `rel="sponsored"` and come with a disclosure line. Add none, and the “Tools we use” box stays off.
4. **Display ads.** Apply for Google AdSense once you have about 20–30 quality posts, then set both `adsenseClient` and `adsenseSlotInArticle`. Either one alone is not enough to render a slot.
5. **SEO basics.** Keep descriptive titles and descriptions (the style guide enforces this), submit `sitemap.xml` to Google Search Console and Bing Webmaster Tools, and share each report on X and LinkedIn. Each report already gets a unique 1200×630 share image (see [Cover images](#cover-images)); set `cover.image` only when you want a custom one.
6. **Quality > volume.** Google penalizes thin, mass-produced AI content. The deep-dive section, the real sources and the "why it matters" analysis are what make these pages worth ranking. Skim each report before it goes out, at least in the first weeks.

## Renaming the site
Change `title`, `params.author`, `params.homeInfoParams.Title`, `copyright` and `params.description` in `hugo.toml`, plus the `AI Brief` prefix in `docs/report-style.md`. If you use n8n, run `python3 n8n/build_workflow.py` afterwards and re-import the workflow.
