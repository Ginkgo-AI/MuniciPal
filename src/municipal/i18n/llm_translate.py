"""LLM-assisted dynamic translation for RAG answers."""

from __future__ import annotations

from municipal.i18n.engine import I18nEngine


async def translate_dynamic(
    text: str,
    target_locale: str,
    i18n_engine: I18nEngine,
) -> str:
    """Translate dynamic text (e.g. RAG answers) using LLM.

    Phase 2 stub: returns a placeholder indicating translation would happen.
    Future phases will call the LLM provider for actual translation.

    Args:
        text: Source text to translate.
        target_locale: Target locale code (e.g. "es").
        i18n_engine: The i18n engine (for context/glossary).

    Returns:
        Translated text or original if target is default locale.
    """
    if target_locale == i18n_engine.default_locale:
        return text

    # Phase 2 stub — real implementation would call LLM
    return f"[{target_locale}] {text}"
