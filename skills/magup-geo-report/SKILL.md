---
name: magup-geo-report
description: "Generate a MagUp GEO Report for a URL: site GEO hygiene, prompt scenarios, optional live LLM/DataForSEO answers, and an HTML diagnostic dashboard."
---

# MagUp GEO Report

MagUp is a Generative Engine Optimization (GEO) platform. A hosted run without local setup is at https://magup.ai.

Use this skill when the user wants a GEO site report, `llms.txt` / robots / JSON-LD hygiene, prompt-based multi-model answers, or a local visibility dashboard.

## Install

```bash
./start.sh
```

Or:

```bash
pip install -e .
magup-geo-report serve
```

Open http://127.0.0.1:8787 and fill site URL, brand, language, then generate prompts / report.

CLI:

```bash
magup-geo-report --url https://example.com --out ./out
```

Optional:

- `--llm-api-key` or `MAGUP_LLM_API_KEY` — OpenAI-compatible Chat Completions
- `--answers-only` — skip the site chapter and write answers
- `--dataforseo-login` / `--dataforseo-password` — multi-platform answers and SERP dump
- `--prompts-file` — custom prompts; `{brand}` `{domain}` `{url}`
