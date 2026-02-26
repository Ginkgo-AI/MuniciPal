"""Tests for shadow mode comparisons and model registry (WP5)."""

from __future__ import annotations

import pytest

from municipal.core.config import LLMConfig
from municipal.llm.registry import ModelRegistry
from municipal.web.mission_control import (
    ShadowComparisonResult,
    ShadowComparisonStore,
    ShadowModeManager,
)


class TestModelRegistry:
    def test_set_and_get_production(self):
        reg = ModelRegistry()
        config = LLMConfig(provider="vllm", base_url="http://prod:8000", model="llama3")
        reg.set_production(config)
        assert reg.get_production() is config

    def test_set_and_get_candidate(self):
        reg = ModelRegistry()
        config = LLMConfig(provider="vllm", base_url="http://cand:8000", model="llama3.1")
        reg.set_candidate(config)
        assert reg.get_candidate() is config
        assert reg.has_candidate() is True

    def test_promote_candidate(self):
        reg = ModelRegistry()
        prod = LLMConfig(provider="vllm", base_url="http://prod:8000", model="old")
        cand = LLMConfig(provider="vllm", base_url="http://cand:8000", model="new")
        reg.set_production(prod)
        reg.set_candidate(cand)

        promoted = reg.promote_candidate()
        assert promoted.model == "new"
        assert reg.get_production().model == "new"
        assert reg.get_candidate() is None
        assert reg.has_candidate() is False

    def test_promote_without_candidate_raises(self):
        reg = ModelRegistry()
        with pytest.raises(ValueError, match="No candidate model"):
            reg.promote_candidate()

    def test_summary(self):
        reg = ModelRegistry()
        prod = LLMConfig(provider="vllm", base_url="http://prod:8000", model="llama3")
        reg.set_production(prod)
        summary = reg.summary()
        assert summary["production"] is not None
        assert summary["production"]["model"] == "llama3"
        assert summary["candidate"] is None


class TestShadowComparisonStore:
    def test_add_and_list(self):
        store = ShadowComparisonStore()
        result = ShadowComparisonResult(
            session_id="sess-1",
            user_message="Hello",
            production_response="Hi there",
            candidate_response="Hey!",
            diverged=True,
        )
        store.add(result)
        assert len(store.list_all()) == 1

    def test_get_for_session(self):
        store = ShadowComparisonStore()
        store.add(ShadowComparisonResult(
            session_id="sess-1", user_message="Q1",
            production_response="A1", candidate_response="A1",
        ))
        store.add(ShadowComparisonResult(
            session_id="sess-2", user_message="Q2",
            production_response="A2", candidate_response="A2",
        ))
        assert len(store.get_for_session("sess-1")) == 1
        assert len(store.get_for_session("sess-2")) == 1

    def test_stats_no_comparisons(self):
        store = ShadowComparisonStore()
        stats = store.stats()
        assert stats["total_comparisons"] == 0
        assert stats["divergence_rate"] == 0.0

    def test_stats_with_divergences(self):
        store = ShadowComparisonStore()
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q", production_response="A",
            candidate_response="B", diverged=True,
        ))
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q", production_response="A",
            candidate_response="A", diverged=False,
        ))
        stats = store.stats()
        assert stats["total_comparisons"] == 2
        assert stats["diverged_count"] == 1
        assert stats["divergence_rate"] == 0.5

    def test_clear(self):
        store = ShadowComparisonStore()
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q",
            production_response="A", candidate_response="A",
        ))
        store.clear()
        assert len(store.list_all()) == 0


class TestShadowModeManagerWithConfig:
    def test_shadow_llm_config_default_none(self):
        mgr = ShadowModeManager()
        assert mgr.shadow_llm_config is None

    def test_set_shadow_llm_config(self):
        mgr = ShadowModeManager()
        config = LLMConfig(provider="vllm", base_url="http://shadow:8000", model="test")
        mgr.shadow_llm_config = config
        assert mgr.shadow_llm_config is config
