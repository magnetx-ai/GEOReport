from __future__ import annotations

import json
import re
from typing import Any

from magup_geo_report.llm_raw import collect_raw_answers

MAX_PROMPTS = 20
DEFAULT_COUNT = 8

# Align with magup_v3 generate-aeo-scenarios / generate-monitoring-prompts:
# unbranded prompts must make AI enumerate vendors, not explain a category.
_TRIGGER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bbest\b",
        r"\btop\b",
        r"\bwhich\b",
        r"\brecommend",
        r"\balternatives?\b",
        r"\bcompare\b",
        r"\bvs\b",
        r"哪些|哪家|哪款|哪一[个個款家]|有哪些",
        r"推荐|推薦|最好|最佳|怎么选|怎麼選|如何选|如何選",
        r"\bmelhores?\b",
        r"\bqual(?:is)?\b",
        r"\bmeilleurs?\b",
        r"\brecommand",
        r"最好|最佳|おすすめ|どの",
        r"أفضل|توصي",
    )
]

_GENERIC_JUNK = re.compile(
    r"(这个|這个|该)\s*(AI\s*)?(平台|工具|产品|產品|服务|服務)|"
    r"能为团队解决哪些|能為團隊解決哪些|"
    r"买家通常如何评估|買家通常如何評估|"
    r"如何做供应商短名单|如何做供應商短名單|"
    r"how do (?:buyers|teams) (?:evaluate|shortlist)|"
    r"what should a company look for when choosing a provider|"
    r"which factors matter most in this category",
    re.IGNORECASE,
)

_BRANDED = {
    "en": [
        "What does {brand} actually do, and who is it for?",
        "Is the official {brand} website a reliable place to verify product details?",
        "What should I check before choosing {brand}?",
        "Does {brand} fit a team that needs {axis}?",
        "What are common alternatives to {brand}?",
        "How is {brand} usually described — and what might be outdated or wrong?",
        "What limitations should I know about before using {brand}?",
        "Can {brand} handle {axis} in a real buying scenario?",
    ],
    "zh-Hans": [
        "{brand} 具体做什么、适合谁？",
        "{brand} 的官网信息靠谱吗，去哪核实产品细节？",
        "选 {brand} 之前应该确认哪些能力？",
        "{brand} 适不适合需要「{axis}」的团队？",
        "{brand} 常见的替代选择有哪些？",
        "外界通常怎么介绍 {brand}，有哪些说法可能不准？",
        "用 {brand} 之前要知道哪些限制？",
        "{brand} 能不能覆盖「{axis}」这种实际采购场景？",
    ],
    "ja": [
        "{brand} は実際に何をして、誰向けですか？",
        "{brand} の公式サイトで製品情報を確認できますか？",
        "{brand} を選ぶ前に何を確認すべきですか？",
        "{axis} が必要なチームに {brand} は向いていますか？",
        "{brand} の代替には何がありますか？",
        "{brand} の一般的な説明で、古いか間違っている点はありますか？",
        "{brand} を使う前に知るべき制限は何ですか？",
        "{brand} は {axis} の実務に耐えますか？",
    ],
    "fr": [
        "Que fait vraiment {brand} et pour qui ?",
        "Le site officiel de {brand} permet-il de vérifier les détails produit ?",
        "Que faut-il vérifier avant de choisir {brand} ?",
        "{brand} convient-il à une équipe qui a besoin de {axis} ?",
        "Quelles sont les alternatives courantes à {brand} ?",
        "Comment {brand} est-il décrit, et que pourrait être inexact ?",
        "Quelles limites connaître avant d'utiliser {brand} ?",
        "{brand} peut-il couvrir {axis} dans un vrai achat ?",
    ],
    "pt-PT": [
        "O que é que {brand} faz realmente e para quem?",
        "O site oficial de {brand} serve para verificar detalhes do produto?",
        "O que confirmar antes de escolher {brand}?",
        "{brand} serve uma equipa que precisa de {axis}?",
        "Quais são alternativas comuns a {brand}?",
        "Como {brand} é descrito — o que pode estar desatualizado?",
        "Que limitações conhecer antes de usar {brand}?",
        "{brand} consegue cobrir {axis} numa compra real?",
    ],
    "pt-BR": [
        "O que a {brand} realmente faz e para quem?",
        "O site oficial da {brand} serve para verificar detalhes do produto?",
        "O que checar antes de escolher a {brand}?",
        "A {brand} serve um time que precisa de {axis}?",
        "Quais são alternativas comuns à {brand}?",
        "Como a {brand} é descrita — o que pode estar desatualizado?",
        "Que limitações saber antes de usar a {brand}?",
        "A {brand} consegue cobrir {axis} numa compra real?",
    ],
    "ar": [
        "ماذا يفعل {brand} فعليًا ولمن؟",
        "هل الموقع الرسمي لـ {brand} مكان موثوق للتحقق من تفاصيل المنتج؟",
        "ماذا يجب التحقق منه قبل اختيار {brand}؟",
        "هل {brand} مناسب لفريق يحتاج {axis}؟",
        "ما البدائل الشائعة لـ {brand}؟",
        "كيف يُوصف {brand} عادة، وما الذي قد يكون غير دقيق؟",
        "ما القيود التي يجب معرفتها قبل استخدام {brand}؟",
        "هل يستطيع {brand} تغطية {axis} في سيناريو شراء حقيقي؟",
    ],
}

_UNBRANDED = {
    "en": [
        "What are the best options for {axis}?",
        "Which providers would you recommend for {axis}?",
        "I'm comparing tools for {axis} — which brands should I shortlist?",
        "Who offers a reliable solution for {axis} without locking us in?",
        "What are the top alternatives if we need {axis} for a mid-size team?",
        "Which platforms are worth trying first for {axis}?",
    ],
    "zh-Hans": [
        "有哪些适合「{axis}」的方案值得推荐？",
        "做「{axis}」的话，哪几家比较靠谱？",
        "我想找能覆盖「{axis}」的工具，有哪些品牌值得列入短名单？",
        "中小团队做「{axis}」，有哪些平台值得先试？",
        "「{axis}」这个需求，最好选哪类产品？",
        "有哪些可以替代的选择，适合「{axis}」这种场景？",
    ],
    "ja": [
        "{axis} におすすめの選択肢は何ですか？",
        "{axis} なら、どの提供元が比較的信頼できますか？",
        "{axis} 向けツールを比較したいです。どのブランドを候補にすべきですか？",
        "{axis} が必要な中小チームなら、まずどのプラットフォームを試すべきですか？",
        "{axis} にはどのタイプの製品が向いていますか？",
        "{axis} の代替として検討すべきものは何ですか？",
    ],
    "fr": [
        "Quelles sont les meilleures options pour {axis} ?",
        "Quels prestataires recommanderiez-vous pour {axis} ?",
        "Je compare des outils pour {axis} — quelles marques shortlister ?",
        "Qui propose une solution fiable pour {axis} ?",
        "Quelles plateformes essayer en premier pour {axis} ?",
        "Quelles alternatives pour {axis} en équipe mid-size ?",
    ],
    "pt-PT": [
        "Quais são as melhores opções para {axis}?",
        "Que fornecedores recomenda para {axis}?",
        "Estou a comparar ferramentas para {axis} — que marcas devo considerar?",
        "Quem oferece uma solução fiável para {axis}?",
        "Que plataformas vale a pena experimentar primeiro para {axis}?",
        "Quais alternativas para {axis} numa equipa média?",
    ],
    "pt-BR": [
        "Quais são as melhores opções para {axis}?",
        "Que fornecedores você recomendaria para {axis}?",
        "Estou comparando ferramentas para {axis} — quais marcas colocar na shortlist?",
        "Quem oferece uma solução confiável para {axis}?",
        "Quais plataformas vale testar primeiro para {axis}?",
        "Quais alternativas para {axis} num time de médio porte?",
    ],
    "ar": [
        "ما أفضل الخيارات لـ {axis}؟",
        "أي مزودين توصي بهم لـ {axis}؟",
        "أقارن أدوات لـ {axis} — أي علامات أضعها في القائمة المختصرة؟",
        "من يقدم حلاً موثوقًا لـ {axis}؟",
        "أي منصات تستحق التجربة أولاً لـ {axis}؟",
        "ما البدائل المناسبة لـ {axis} لفريق متوسط الحجم؟",
    ],
}


def _pool(table: dict[str, list[str]], language: str) -> list[str]:
    return list(table.get(language) or table["en"])


def _category_axis(brand: str, intro: str, extra_notes: str = "") -> str:
    text = " ".join(part for part in (intro, extra_notes) if part and part.strip()).strip()
    if not text:
        return ""
    first = re.split(r"[。.!?\n；;，,]", text)[0].strip()
    if brand:
        first = re.sub(re.escape(brand), "", first, flags=re.IGNORECASE)
    first = first.strip(" ，,的是为為-—:：")
    if len(first) > 32:
        first = first[:32].rstrip()
    return first


def _fill(template: str, **fields: str) -> str:
    axis = fields.get("axis") or "this category"
    return template.format(
        brand=fields.get("brand") or "",
        domain=fields.get("domain") or "",
        url=fields.get("url") or "",
        axis=axis,
    )


def generate_prompts_from_templates(
    *,
    brand: str,
    domain: str,
    url: str,
    languages: list[str],
    total: int,
    unbranded_ratio: int,
    competitors: list[str] | None = None,
    brand_intro: str = "",
    extra_notes: str = "",
) -> list[dict[str, str]]:
    total = max(1, min(MAX_PROMPTS, int(total)))
    unbranded_ratio = max(0, min(100, int(unbranded_ratio)))
    unbranded_n = round(total * unbranded_ratio / 100)
    branded_n = total - unbranded_n
    langs = languages or ["en"]
    competitors = [item.strip() for item in (competitors or []) if item.strip()][:4]
    axis = _category_axis(brand, brand_intro, extra_notes)
    if not axis:
        unbranded_n = 0
        branded_n = total
    items: list[dict[str, str]] = []
    index = 0
    while len(items) < branded_n:
        language = langs[len(items) % len(langs)]
        template = _pool(_BRANDED, language)[index % len(_pool(_BRANDED, language))]
        text = _fill(template, brand=brand, domain=domain, url=url, axis=axis or brand)
        if competitors and index == 1:
            joined = " vs ".join([brand, *competitors[:2]])
            extra = {
                "en": f" How does {joined} compare for {axis or 'this use case'}?",
                "zh-Hans": f" {joined} 在「{axis or '这个场景'}」上怎么比？",
                "ja": f" {joined} を {axis or 'この用途'} で比べると？",
                "fr": f" Comment comparer {joined} pour {axis or 'ce besoin'} ?",
                "pt-PT": f" Como se compara {joined} para {axis or 'este caso'}?",
                "pt-BR": f" Como comparar {joined} para {axis or 'esse caso'}?",
                "ar": f" كيف يُقارن {joined} من أجل {axis or 'هذا الاستخدام'}؟",
            }.get(language)
            if extra:
                text = extra.strip()
        items.append(
            {
                "id": f"p{len(items)+1}",
                "language": language,
                "kind": "branded",
                "text": text,
            }
        )
        index += 1
    index = 0
    while len(items) < total:
        language = langs[len(items) % len(langs)]
        template = _pool(_UNBRANDED, language)[index % len(_pool(_UNBRANDED, language))]
        items.append(
            {
                "id": f"p{len(items)+1}",
                "language": language,
                "kind": "unbranded",
                "text": _fill(template, brand=brand, domain=domain, url=url, axis=axis),
            }
        )
        index += 1
    return items


def generate_prompts_with_llm(
    *,
    brand: str,
    domain: str,
    url: str,
    brand_intro: str,
    languages: list[str],
    total: int,
    unbranded_ratio: int,
    competitors: list[str],
    extra_notes: str,
    api_key: str,
    base_url: str,
    model: str,
) -> list[dict[str, str]]:
    """Generate AEO monitoring prompts the same way MagUp production does.

    Craft rules follow magup_v3 `generate-monitoring-prompts` /
    `generate-aeo-scenarios`: grounded in enterprise_info, unbranded vs branded
    pools, recommendation triggers, no fabricated category.
    """
    total = max(1, min(MAX_PROMPTS, int(total)))
    intro = (brand_intro or "").strip()
    notes = (extra_notes or "").strip()
    if not intro:
        raise ValueError("请先填写品牌简介后再用 API 生成提示词")
    langs = languages or ["en"]
    competitors = [item.strip() for item in (competitors or []) if item.strip()][:4]
    unbranded_n = round(total * max(0, min(100, int(unbranded_ratio))) / 100)
    branded_n = total - unbranded_n
    instruction = _llm_instruction(
        brand=brand,
        domain=domain,
        url=url,
        intro=intro,
        notes=notes,
        languages=langs,
        total=total,
        unbranded_n=unbranded_n,
        branded_n=branded_n,
        competitors=competitors,
    )
    raw = collect_raw_answers(
        prompts=[instruction],
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    answer = ""
    items = raw.get("items") or []
    if items:
        answer = items[0].get("answer") or ""
    parsed = _extract_json(answer)
    prompts = parsed.get("prompts") if isinstance(parsed, dict) else None
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("LLM did not return a prompts JSON list")
    cleaned = _clean_llm_prompts(
        prompts,
        brand=brand,
        domain=domain,
        competitors=competitors,
        languages=langs,
        total=total,
        unbranded_n=unbranded_n,
    )
    if len(cleaned) < total:
        fallback = generate_prompts_from_templates(
            brand=brand,
            domain=domain,
            url=url,
            languages=langs,
            total=total,
            unbranded_ratio=unbranded_ratio,
            competitors=competitors,
            brand_intro=intro,
            extra_notes=notes,
        )
        have = {item["text"] for item in cleaned}
        for row in fallback:
            if len(cleaned) >= total:
                break
            if row["text"] in have:
                continue
            if not _is_usable(row["text"], row["kind"], brand, domain, competitors):
                continue
            cleaned.append({**row, "id": f"p{len(cleaned)+1}"})
            have.add(row["text"])
    return cleaned[:total]


def _llm_instruction(
    *,
    brand: str,
    domain: str,
    url: str,
    intro: str,
    notes: str,
    languages: list[str],
    total: int,
    unbranded_n: int,
    branded_n: int,
    competitors: list[str],
) -> str:
    lang_join = ", ".join(langs_label(languages))
    return f"""You generate AEO monitoring prompts for ChatGPT / Gemini / Claude / Perplexity visibility tests.
Follow MagUp generate-monitoring-prompts + generate-aeo-scenarios craft rules.

## Evidence (only source of business facts)
enterprise_info:
{intro}

extra_notes:
{notes or "(none)"}

brand_name: {brand}
domain: {domain}
url: {url}
competitors (branded pool only, sparingly): {", ".join(competitors) or "(none)"}
languages: {lang_join}

Do not invent products, category, ICP, or claims not in enterprise_info.
If a fact is missing, skip it — never guess "AI platform" or a generic SaaS category.

## Counts
Create exactly {total} prompts: {unbranded_n} unbranded, {branded_n} branded.
Distribute across the requested languages. Each prompt is one complete user question.

## Pool A — unbranded (kind=unbranded)
Purpose: test whether AI names real vendors when a buyer asks for recommendations.
- MUST NOT contain brand_name, domain, unique product names, or competitor names.
- MUST name a concrete category / product type / use-case / buyer situation taken from enterprise_info.
- Voice: real buyer talking to ChatGPT. Priority: purchase intent > comparison > category research > use-case.
- ≥60% MUST include a locale recommendation trigger:
  zh: 哪些 / 哪家 / 推荐 / 最好 / 怎么选
  en: best / which / recommend / alternatives
  ja: おすすめ / どの
  fr: meilleur / recommand
  pt: melhor / qual
  ar: أفضل / توصية
- How-to and vague questions are forbidden (they do not surface brands).
- Prefer ≤45 Chinese characters or ≤22 English words.

## Pool B — branded (kind=branded)
Purpose: test fact accuracy and official-site understanding.
- MUST include brand_name.
- Ask about what it does, who it is for, capabilities, limits, official site, or fit to a use-case in enterprise_info.
- Do not append (官网：{domain}) or (official site: {domain}).
- No marketing hype.

## Forbidden (unusable)
- 这个 AI 平台能为团队解决哪些实际问题？
- 买家通常如何评估这个市场里的供应商？
- How do teams shortlist vendors?
- What should a company look for when choosing a provider?
- Any question whose category is only "this platform / this tool / this market".

## Good
- 跨境电商独立站想做白标企业信用卡，有哪些平台值得推荐？
- Which platforms offer white-label corporate card programs for fintech startups expanding internationally?
- What are the best ND filter brands for landscape photography under $80, and which have the least color cast?
- {brand} 具体做什么，官网信息靠谱吗？
- Does {brand} support the use-case described in enterprise_info?

Return JSON only, no markdown:
{{"prompts": [{{"language": "{languages[0]}", "kind": "unbranded", "text": "..."}}]}}
"""


def langs_label(languages: list[str]) -> list[str]:
    return languages or ["en"]


def _has_trigger(text: str) -> bool:
    return any(pattern.search(text) for pattern in _TRIGGER_PATTERNS)


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle and needle.lower() in lowered for needle in needles)


def _is_usable(text: str, kind: str, brand: str, domain: str, competitors: list[str]) -> bool:
    value = (text or "").strip()
    if len(value) < 8:
        return False
    if _GENERIC_JUNK.search(value):
        return False
    blocked = [brand, domain, *competitors]
    if kind == "unbranded":
        if _contains_any(value, blocked):
            return False
        return _has_trigger(value)
    return _contains_any(value, [brand])


def _clean_llm_prompts(
    rows: list[Any],
    *,
    brand: str,
    domain: str,
    competitors: list[str],
    languages: list[str],
    total: int,
    unbranded_n: int,
) -> list[dict[str, str]]:
    default_lang = languages[0] if languages else "en"
    cleaned: list[dict[str, str]] = []
    unbranded_kept = 0
    for row in rows:
        if len(cleaned) >= total:
            break
        if isinstance(row, str):
            text = row.strip()
            kind = "branded" if _contains_any(text, [brand]) else "unbranded"
            language = default_lang
        elif isinstance(row, dict):
            text = str(row.get("text") or row.get("prompt") or "").strip()
            language = str(row.get("language") or default_lang)
            kind = str(row.get("kind") or ("branded" if _contains_any(text, [brand]) else "unbranded"))
        else:
            continue
        if kind not in {"branded", "unbranded"}:
            kind = "branded" if _contains_any(text, [brand]) else "unbranded"
        if kind == "unbranded" and unbranded_kept >= unbranded_n:
            kind = "branded"
        if not _is_usable(text, kind, brand, domain, competitors):
            continue
        if kind == "unbranded":
            unbranded_kept += 1
        cleaned.append(
            {
                "id": f"p{len(cleaned)+1}",
                "language": language,
                "kind": kind,
                "text": text,
            }
        )
    return cleaned


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
