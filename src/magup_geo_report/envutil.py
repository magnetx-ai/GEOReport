from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path | None = None) -> None:
    candidate = path or Path.cwd() / ".env"
    if not candidate.is_file():
        return
    for raw in candidate.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def env_get(name: str, *aliases: str) -> str | None:
    for key in (name, *aliases):
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    return None


def mask_secret(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    n = len(text)
    if n <= 6:
        return text[0] + "•" * max(3, n - 1)
    keep = 4 if n >= 20 else 3 if n >= 12 else 2
    bullets = min(8, max(4, n - keep * 2))
    return f"{text[:keep]}{'•' * bullets}{text[-keep:]}"


def mask_login(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if "@" in text:
        local, _, domain = text.partition("@")
        if len(local) <= 2:
            shown = local[:1] + "•"
        else:
            shown = local[:2] + "•••"
        return f"{shown}@{domain}"
    return mask_secret(text)


def looks_masked(value: str | None) -> bool:
    text = (value or "").strip()
    return bool(text) and "•" in text


def env_status() -> dict[str, bool | str | None]:
    load_dotenv()
    llm_key = env_get("MAGUP_LLM_API_KEY", "OPENAI_API_KEY")
    dfs_login = env_get("DATAFORSEO_LOGIN")
    dfs_password = env_get("DATAFORSEO_PASSWORD")
    return {
        "llm": bool(llm_key),
        "dataforseo": bool(dfs_login and dfs_password),
        "llm_api_key": mask_secret(llm_key),
        "llm_base_url": env_get("MAGUP_LLM_BASE_URL"),
        "llm_model": env_get("MAGUP_LLM_MODEL"),
        "dataforseo_login": mask_login(dfs_login),
        "dataforseo_password": mask_secret(dfs_password),
    }


def resolve_keys(
    *,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    dataforseo_login: str | None = None,
    dataforseo_password: str | None = None,
) -> dict[str, str | None]:
    """Page values win when a key is pasted. Otherwise use .env / process env."""
    load_dotenv()
    form_key = (llm_api_key or "").strip()
    if looks_masked(form_key):
        form_key = ""
    form_login = (dataforseo_login or "").strip()
    form_password = (dataforseo_password or "").strip()
    if looks_masked(form_login):
        form_login = ""
    if looks_masked(form_password):
        form_password = ""
    if form_key:
        key = form_key
        base = (llm_base_url or "").strip() or env_get("MAGUP_LLM_BASE_URL") or "https://api.openai.com/v1"
        model = (llm_model or "").strip() or env_get("MAGUP_LLM_MODEL") or "gpt-4o-mini"
    else:
        key = env_get("MAGUP_LLM_API_KEY", "OPENAI_API_KEY")
        base = (llm_base_url or "").strip() or env_get("MAGUP_LLM_BASE_URL") or "https://api.openai.com/v1"
        model = (llm_model or "").strip() or env_get("MAGUP_LLM_MODEL") or "gpt-4o-mini"
    return {
        "llm_api_key": key,
        "llm_base_url": base,
        "llm_model": model,
        "dataforseo_login": form_login or env_get("DATAFORSEO_LOGIN"),
        "dataforseo_password": form_password or env_get("DATAFORSEO_PASSWORD"),
    }
