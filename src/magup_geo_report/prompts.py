from __future__ import annotations

from pathlib import Path

MAX_BUILTIN = 8

# Generic prompts. Not MagUp's closed questionType generator.
# Placeholders: {brand} {domain} {url}
BUILTIN_PROMPTS = [
    "What is {brand}?",
    "What does {brand} ({domain}) do, and who is it for?",
    "What is the official website of {brand}?",
    "How is {brand} typically described as a product or company?",
    "What are commonly mentioned alternatives to {brand}?",
    "What should someone know before choosing {brand}?",
    "How is {brand} usually compared with competitors?",
    "Summarize {brand} in one short paragraph using only well-known public facts.",
]


def load_prompts(path: str | None) -> list[str]:
    if not path:
        return list(BUILTIN_PROMPTS)
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    prompts = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    if not prompts:
        raise ValueError(f"no prompts in {path}")
    return prompts


def fill_prompts(prompts: list[str], *, brand: str, domain: str, url: str) -> list[str]:
    filled = []
    for prompt in prompts:
        filled.append(
            prompt.format(brand=brand, domain=domain, url=url)
        )
    return filled
