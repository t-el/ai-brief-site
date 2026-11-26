#!/usr/bin/env python3
"""Regenerate n8n/ai-brief-workflow.json (embeds docs/report-style.md into the LLM system prompt)."""
import json, os, uuid
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
def nid(): return str(uuid.uuid4())

FEEDS = [
  ["OpenAI News", "https://openai.com/news/rss.xml", 10],
  ["Google DeepMind Blog", "https://deepmind.google/blog/rss.xml", 10],
  ["Google AI (The Keyword)", "https://blog.google/technology/ai/rss/", 10],
  ["Hugging Face Blog", "https://huggingface.co/blog/feed.xml", 10],
  ["TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", 15],
  ["The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", 15],
  ["MIT Technology Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed", 10],
  ["Hacker News (AI, 100+ pts)", "https://hnrss.org/newest?q=AI+OR+LLM+OR+OpenAI+OR+Anthropic+OR+Gemini&points=100", 15],
  ["arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI", 5],
]

style = open("docs/report-style.md").read()

SYSTEM_PROMPT = """You are the senior editor of "AI Brief Daily", a sourced, skeptical daily AI news site.
You receive a JSON list of news items from the last 24 hours (title, link, source, published, snippet).
Write ONE daily deep report in Markdown with Hugo YAML front matter, following the STYLE GUIDE below exactly.

Hard rules:
- Output ONLY the Markdown file content, starting with the line '---'. No code fences, no commentary.
- Use ONLY facts present in the provided items. Never invent numbers, quotes, dates, people or URLs.
- Every link you output must be one of the provided item links.
- Pick the 4-6 most important stories (dedupe items covering the same event; cite all of them under that story).
- Prefer primary sources (lab blogs, papers) and say "X says..." for company claims.
- No raw HTML. Plain English, no hype words.
- Front matter 'date' and 'lastmod' must equal the REPORT_DATETIME given by the user; title must start with 'AI Brief — <REPORT_DATE_HUMAN>:'.
- categories must be exactly ["Daily Report"]. draft: false.

STYLE GUIDE:
""" + style

FEEDS_CODE = "const feeds = " + json.dumps([{"source": s, "url": u, "max": m} for s, u, m in FEEDS], indent=2) + ";\nreturn feeds.map(f => ({ json: f }));\n"

DEDUPE_CODE = r"""// Merge all feed items, keep last N hours, dedupe, rank, cap, then build the LLM request body.
const cfg = $('Config').first().json;
const feeds = $('RSS Feed List').all().map(i => i.json);
const hours = Number(cfg.lookbackHours) || 24;
const cutoff = Date.now() - hours * 3600 * 1000;

const rssItems = $input.all()
  .map(i => ({ ...i.json, _feedIdx: i.pairedItem && typeof i.pairedItem.item === 'number' ? i.pairedItem.item : -1 }))
  .filter(j => j && (j.link || j.guid));

// Map each item back to its feed via n8n pairedItem; fall back to hostname matching.
const host = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; } };
const feedFor = link => feeds.find(f => host(link).endsWith(host(f.url).replace(/^(rss|news)\./, ''))) || { source: host(link), max: 10 };

const norm = s => (s || '').toLowerCase().replace(/https?:\/\/(www\.)?/, '').replace(/[?#].*$/, '').replace(/[^a-z0-9]+/g, ' ').trim();
const seenLinks = new Set(), seenTitles = new Set(), perSource = {};
const out = [];

for (const j of rssItems) {
  const link = (j.link || j.guid || '').trim();
  const ts = Date.parse(j.isoDate || j.pubDate || '');
  if (!link || isNaN(ts) || ts < cutoff) continue;
  const lk = norm(link), tk = norm(j.title).split(' ').slice(0, 10).join(' ');
  if (seenLinks.has(lk) || (tk && seenTitles.has(tk))) continue;
  const f = feeds[j._feedIdx] || feedFor(link);
  perSource[f.source] = (perSource[f.source] || 0) + 1;
  if (perSource[f.source] > f.max) continue;
  seenLinks.add(lk); if (tk) seenTitles.add(tk);
  const snippet = (j.contentSnippet || j.content || j.summary || '').replace(/\s+/g, ' ').slice(0, 600);
  out.push({ title: (j.title || '').trim(), link, source: f.source, published: new Date(ts).toISOString(), snippet });
}

out.sort((a, b) => b.published.localeCompare(a.published));
const items = out.slice(0, Number(cfg.maxItems) || 60);
if (items.length < 4) throw new Error(`Only ${items.length} fresh items in the last ${hours}h, skipping today's report.`);

// Report date in Africa/Casablanca
const tz = cfg.timezone || 'Africa/Casablanca';
const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZoneName: 'longOffset' })
  .formatToParts(new Date()).map(p => [p.type, p.value]));
const reportDate = `${parts.year}-${parts.month}-${parts.day}`;
let offset = (parts.timeZoneName || 'GMT').replace('GMT', '') || '+00:00';
if (!offset.includes(':')) offset = '+00:00';
const reportDateTime = `${reportDate}T${parts.hour}:${parts.minute}:00${offset}`;
const human = new Date(`${reportDate}T12:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });

const body = {
  model: cfg.model,
  temperature: Number(cfg.temperature) || 0.3,
  max_tokens: Number(cfg.maxTokens) || 6000,
  messages: [
    { role: 'system', content: cfg.systemPrompt },
    { role: 'user', content: `REPORT_DATE: ${reportDate}\nREPORT_DATE_HUMAN: ${human}\nREPORT_DATETIME: ${reportDateTime}\n\nNEWS ITEMS (${items.length}) as JSON:\n${JSON.stringify(items, null, 1)}` }
  ]
};

return [{ json: { reportDate, reportDateTime, itemCount: items.length, body } }];
"""

PREP_CODE = r"""// Extract the markdown, sanity-check it, and build the GitHub Contents API payload.
const cfg = $('Config').first().json;
const meta = $('Merge, Dedupe & Build Prompt').first().json;
const res = $input.first().json;

let md = (res.choices && res.choices[0] && res.choices[0].message && res.choices[0].message.content) || '';
md = md.trim().replace(/^```(?:markdown|md)?\s*\n/i, '').replace(/\n```\s*$/, '').trim() + '\n';

const required = ['## TL;DR', '## Top stories', '## Deep dive', '## Sources'];
const missing = required.filter(h => !md.includes(h));
if (!md.startsWith('---')) missing.push('front matter');
if (/^draft:\s*true/m.test(md)) missing.push('draft must be false');
if (missing.length) throw new Error('LLM output failed format check: ' + missing.join(', '));

const path = `${cfg.contentDir}/${meta.reportDate}.md`;
return [{ json: {
  path,
  apiUrl: `https://api.github.com/repos/${cfg.githubOwner}/${cfg.githubRepo}/contents/${path}`,
  message: `report: ${meta.reportDate}`,
  contentBase64: Buffer.from(md, 'utf8').toString('base64'),
  branch: cfg.githubBranch,
  markdown: md
} }];
"""

GH_HEADERS = {"parameters": [
  {"name": "Accept", "value": "application/vnd.github+json"},
  {"name": "X-GitHub-Api-Version", "value": "2022-11-28"},
  {"name": "User-Agent", "value": "ai-brief-n8n"}]}

GH_CRED = {"httpHeaderAuth": {"id": "REPLACE_WITH_GITHUB_CREDENTIAL_ID", "name": "GitHub fine-grained token (Header Auth)"}}
LLM_CRED = {"httpHeaderAuth": {"id": "REPLACE_WITH_LLM_CREDENTIAL_ID", "name": "LLM API key (Header Auth)"}}

nodes = []
def node(name, type_, ver, pos, params, **extra):
    n = {"parameters": params, "id": nid(), "name": name, "type": type_, "typeVersion": ver, "position": pos}
    n.update(extra); nodes.append(n); return n

node("Daily 07:00 Casablanca", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 300],
     {"rule": {"interval": [{"field": "cronExpression", "expression": "0 7 * * *"}]}})

cfg_fields = [
  ("llmBaseUrl", "https://api.openai.com/v1", "string"),
  ("model", "gpt-4.1", "string"),
  ("temperature", 0.3, "number"),
  ("maxTokens", 6000, "number"),
  ("lookbackHours", 24, "number"),
  ("maxItems", 60, "number"),
  ("timezone", "Africa/Casablanca", "string"),
  ("githubOwner", "t-el", "string"),
  ("githubRepo", "ai-brief-site", "string"),
  ("githubBranch", "main", "string"),
  ("contentDir", "content/reports", "string"),
  ("systemPrompt", SYSTEM_PROMPT, "string"),
]
node("Config", "n8n-nodes-base.set", 3.4, [220, 300], {
  "mode": "manual",
  "assignments": {"assignments": [{"id": nid(), "name": k, "value": v, "type": t} for k, v, t in cfg_fields]},
  "options": {}
}, notes="Edit here: LLM base URL (any OpenAI-compatible endpoint, e.g. OpenAI, OpenRouter, Groq, xAI, DeepSeek, local), model, repo owner/name.")

node("RSS Feed List", "n8n-nodes-base.code", 2, [440, 300], {"jsCode": FEEDS_CODE},
     notes="Add/remove feeds here. 'max' caps items per source.")

node("Read RSS", "n8n-nodes-base.rssFeedRead", 1.1, [660, 300],
     {"url": "={{ $json.url }}", "options": {"ignoreSSL": False}},
     onError="continueRegularOutput", retryOnFail=True, maxTries=2, waitBetweenTries=3000,
     notes="One request per feed. A failing feed doesn't stop the run.")

node("Merge, Dedupe & Build Prompt", "n8n-nodes-base.code", 2, [880, 300], {"jsCode": DEDUPE_CODE})

node("LLM: Write Deep Report", "n8n-nodes-base.httpRequest", 4.2, [1100, 300], {
  "method": "POST",
  "url": "={{ $('Config').first().json.llmBaseUrl.replace(/\\/$/, '') }}/chat/completions",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendBody": True,
  "specifyBody": "json",
  "jsonBody": "={{ JSON.stringify($json.body) }}",
  "options": {"timeout": 240000}
}, credentials=LLM_CRED, retryOnFail=True, maxTries=3, waitBetweenTries=5000,
   notes="Header Auth credential: Name = Authorization, Value = Bearer YOUR_API_KEY")

node("Validate & Prepare File", "n8n-nodes-base.code", 2, [1320, 300], {"jsCode": PREP_CODE})

node("GitHub: Get Existing File SHA", "n8n-nodes-base.httpRequest", 4.2, [1540, 300], {
  "method": "GET",
  "url": "={{ $json.apiUrl }}",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendQuery": True,
  "queryParameters": {"parameters": [{"name": "ref", "value": "={{ $json.branch }}"}]},
  "sendHeaders": True,
  "headerParameters": GH_HEADERS,
  "options": {"response": {"response": {"neverError": True, "fullResponse": True}}}
}, credentials=GH_CRED,
   notes="404 = new file (normal). 200 = file exists, so its sha is reused to overwrite.")

node("GitHub: Commit Report to main", "n8n-nodes-base.httpRequest", 4.2, [1760, 300], {
  "method": "PUT",
  "url": "={{ $('Validate & Prepare File').first().json.apiUrl }}",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": True,
  "headerParameters": GH_HEADERS,
  "sendBody": True,
  "specifyBody": "json",
  "jsonBody": "={{ JSON.stringify(Object.assign({ message: $('Validate & Prepare File').first().json.message, content: $('Validate & Prepare File').first().json.contentBase64, branch: $('Validate & Prepare File').first().json.branch, committer: { name: 'AI Brief Bot', email: 'ai-brief-bot@users.noreply.github.com' } }, ($json.statusCode === 200 && $json.body && $json.body.sha) ? { sha: $json.body.sha } : {})) }}",
  "options": {}
}, credentials=GH_CRED,
   notes="Header Auth credential: Name = Authorization, Value = Bearer github_pat_... (fine-grained, this repo only, Contents: Read and write). The push to main triggers the GitHub Pages deploy.")

names = [n["name"] for n in nodes]
connections = {a: {"main": [[{"node": b, "type": "main", "index": 0}]]} for a, b in zip(names, names[1:])}

wf = {
  "name": "AI Brief Daily: RSS → LLM deep report → GitHub (Hugo)",
  "nodes": nodes,
  "connections": connections,
  "settings": {"executionOrder": "v1", "timezone": "Africa/Casablanca", "saveManualExecutions": True},
  "pinData": {},
  "active": False,
  "meta": {"templateCredsSetupCompleted": False},
  "tags": []
}
json.dump(wf, open("n8n/ai-brief-workflow.json", "w"), indent=2, ensure_ascii=False)
print("nodes:", len(nodes))
