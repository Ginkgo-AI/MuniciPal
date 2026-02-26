"""i18n engine — loads YAML translation bundles with dot-notation key lookup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_BUNDLES_DIR = Path(__file__).resolve().parents[3] / "config" / "i18n"


class I18nEngine:
    """Internationalization engine.

    Loads YAML translation bundles from a directory (one file per locale).
    Supports dot-notation key lookup with fallback to default locale.
    """

    def __init__(
        self,
        bundles_dir: str | Path | None = None,
        default_locale: str = "en",
    ) -> None:
        self._bundles_dir = Path(bundles_dir) if bundles_dir else _DEFAULT_BUNDLES_DIR
        self._default_locale = default_locale
        self._bundles: dict[str, dict[str, Any]] = {}
        self._load_bundles()

    def _load_bundles(self) -> None:
        if not self._bundles_dir.exists():
            return
        for path in sorted(self._bundles_dir.glob("*.yml")):
            locale = path.stem
            with open(path) as fh:
                data = yaml.safe_load(fh) or {}
            self._bundles[locale] = data

    @property
    def locales(self) -> list[str]:
        return sorted(self._bundles.keys())

    @property
    def default_locale(self) -> str:
        return self._default_locale

    def get_bundle(self, locale: str) -> dict[str, Any]:
        return self._bundles.get(locale, {})

    def t(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        """Translate a key using dot-notation lookup.

        Falls back to default locale if key not found in requested locale.
        Falls back to the key itself if not found anywhere.

        Args:
            key: Dot-separated path like "wizard.permit.title".
            locale: Target locale. Defaults to default_locale.
            **kwargs: Interpolation variables.

        Returns:
            Translated string.
        """
        locale = locale or self._default_locale
        value = self._resolve(key, locale)
        if value is None and locale != self._default_locale:
            value = self._resolve(key, self._default_locale)
        if value is None:
            return key

        # Simple string interpolation
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except (KeyError, IndexError):
                return value
        return str(value)

    def _resolve(self, key: str, locale: str) -> str | None:
        bundle = self._bundles.get(locale)
        if bundle is None:
            return None

        parts = key.split(".")
        current: Any = bundle
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None

        return str(current) if current is not None else None
