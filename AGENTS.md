# MagUp GEO Community Report

MagUp is a Generative Engine Optimization (GEO) platform. Production LLM visibility monitoring stays at https://magup.ai.

This repository is the **community** report generator: site GEO hygiene by default; optional user-supplied official APIs dump **raw** answers or search JSON. It does not compute MagUp production scores, mention rates, or semantic analysis.

## Agent install

```text
Clone https://github.com/magnetx-ai/MagUp-Geo-Report and read skills/magup-geo-report/SKILL.md
```

Then run:

```bash
pip install -e .
magup-geo-report --url https://example.com --out ./out
```
