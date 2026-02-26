"""Tests for i18n engine."""

from __future__ import annotations

import pytest

from municipal.i18n.engine import I18nEngine


@pytest.fixture
def engine():
    return I18nEngine()


@pytest.fixture
def custom_engine(tmp_path):
    import yaml

    en = {
        "greeting": "Hello {name}",
        "nested": {"key": "Nested Value"},
        "only_en": "English Only",
    }
    es = {
        "greeting": "Hola {name}",
        "nested": {"key": "Valor Anidado"},
    }

    bundles_dir = tmp_path / "i18n"
    bundles_dir.mkdir()
    with open(bundles_dir / "en.yml", "w") as fh:
        yaml.dump(en, fh)
    with open(bundles_dir / "es.yml", "w") as fh:
        yaml.dump(es, fh)

    return I18nEngine(bundles_dir=bundles_dir)


class TestI18nEngine:
    def test_loads_default_bundles(self, engine):
        assert "en" in engine.locales
        assert "es" in engine.locales

    def test_default_locale(self, engine):
        assert engine.default_locale == "en"

    def test_translate_english(self, engine):
        result = engine.t("system.welcome", "en")
        assert result == "Welcome to Munici-Pal"

    def test_translate_spanish(self, engine):
        result = engine.t("system.welcome", "es")
        assert result == "Bienvenido a Munici-Pal"

    def test_nested_key(self, engine):
        result = engine.t("wizard.permit.title", "en")
        assert result == "Permit Application"

    def test_fallback_to_default_locale(self, custom_engine):
        # "only_en" exists in en but not es
        result = custom_engine.t("only_en", "es")
        assert result == "English Only"

    def test_fallback_to_key(self, custom_engine):
        result = custom_engine.t("nonexistent.key", "en")
        assert result == "nonexistent.key"

    def test_string_interpolation(self, custom_engine):
        result = custom_engine.t("greeting", "en", name="World")
        assert result == "Hello World"
        result_es = custom_engine.t("greeting", "es", name="Mundo")
        assert result_es == "Hola Mundo"

    def test_get_bundle(self, engine):
        bundle = engine.get_bundle("en")
        assert "system" in bundle
        assert bundle == engine.get_bundle("en")

    def test_get_bundle_unknown_locale(self, engine):
        bundle = engine.get_bundle("fr")
        assert bundle == {}
