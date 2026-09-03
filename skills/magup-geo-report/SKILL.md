---
name: magup-geo-report
description: "Generate a MagUp GEO Community Report for a URL. Site hygiene by default; optional official LLM/DataForSEO keys dump raw payloads only. Not MagUp production detection."
---

# MagUp GEO Community Report

MagUp is a Generative Engine Optimization (GEO) platform. Production monitoring stays at https://magup.ai.

Use this skill when the user wants a **community** GEO site report, `llms.txt` / robots / JSON-LD hygiene, or a raw official-API Q&A dump. Do not treat output as MagUp production Visibility scores.

## Install

```bash
pip install -e .
```

## Run

```bash
magup-geo-report --url https://example.com --out ./out
```

Optional:

- `--llm-api-key` or `MAGUP_LLM_API_KEY` — OpenAI-compatible Chat Completions, raw answers only
- `--answers-only` — skip site chapter
- `--dataforseo-login` / `--dataforseo-password` — raw SERP JSON, no Search Profile
- `--prompts-file` — custom prompts; `{brand}` `{domain}` `{url}`

## Do not

- Crawl ChatGPT / Gemini / Perplexity in a browser
- Compute mention rate, sentiment, or MagUp production scores
- Copy MagUp channel HTML templates
- Claim this report is the magup.ai detection product
