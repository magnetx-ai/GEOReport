# MagUp GEO Community Report

**MagUp** is a Generative Engine Optimization (GEO) platform. Production LLM visibility monitoring, multi-model answer capture, and semantic analysis remain proprietary at [magup.ai](https://magup.ai).

This repository publishes a **community** report generator:

- Default (no API keys): site GEO hygiene — `robots.txt`, AI crawler groups, `llms.txt`, sitemap, JSON-LD, title/H1.
- Optional official Chat Completions key: **raw** prompt → answer dump. No mention rate, no sentiment, no Visibility score.
- Optional DataForSEO credentials: **raw** SERP JSON. Not MagUp Search Profile.

This is **not** a MagUp production detection report.

中文：MagUp 是 GEO 平台。本仓是**社区精简报告**；完整检测与生产评分只在 [magup.ai](https://magup.ai)。默认不配密钥也能跑站点卫生检查；配了官方 LLM / DataForSEO 密钥也只落原始数据，不做分析。

## What this is / is not

| This community tool | MagUp production (`magup.ai`) |
| --- | --- |
| Local CLI, your machine | Hosted detection pipeline |
| Site GEO hygiene checklist | Multi-model LLM visibility |
| Raw answers if you bring an official API key | Answer capture at scale + analysis |
| Raw DataForSEO JSON if you bring keys | Search Profile + composite scoring + MagUp HTML/poster |
| Apache-2.0 | Closed SaaS |

## Install

Python 3.10+.

```bash
git clone https://github.com/magnetx-ai/MagUp-Geo-Report.git
cd MagUp-Geo-Report
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Zero-config (Option A content):

```bash
magup-geo-report --url https://example.com --out ./out
```

Writes `out/community-report.html`, `out/community-report.md`, `out/site-audit.json`.

Optional raw LLM answers (OpenAI-compatible Chat Completions only — no browser crawler):

```bash
export MAGUP_LLM_API_KEY=sk-...
magup-geo-report --url https://example.com --out ./out
```

Answers only, skip the site chapter:

```bash
magup-geo-report --url https://example.com --answers-only --llm-api-key sk-... --out ./out
```

Optional raw DataForSEO dump:

```bash
export DATAFORSEO_LOGIN=...
export DATAFORSEO_PASSWORD=...
magup-geo-report --url https://example.com --out ./out
```

Custom prompts (one per line; `{brand}` `{domain}` `{url}` placeholders):

```bash
magup-geo-report --url https://example.com --prompts-file examples/prompts.example.txt --out ./out
```

Optional keys: copy [`env.example`](env.example) into your shell environment. The CLI runs with none of them. Built-in list is 8 generic prompts — not MagUp’s production prompt generator.

## Agent Skill

See [`skills/magup-geo-report/SKILL.md`](skills/magup-geo-report/SKILL.md). Cursor / Claude: clone this repo and open that file.

## Hard limits (intentional)

- No Playwright / browser automation against ChatGPT or other LLM UIs
- No Scrapeless, no MagUp LLM Answer Gateway, no account warmup
- No `analyze-llm-answer`, no presence/absence, no composite 5d/100 scoring
- No Magup channel HTML or share posters

Need those? Use the product: [magup.ai](https://magup.ai)

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Entity

- Product: **MagUp** / **MagUp GEO**
- Display name: **MagUp GEO Community Report**
- Site: https://magup.ai
- Code: https://github.com/magnetx-ai/MagUp-Geo-Report
