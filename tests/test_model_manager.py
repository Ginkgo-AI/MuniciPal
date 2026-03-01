"""Tests for ModelManager and enhanced session management."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from municipal.chat.session import ChatMessage, ChatSession, MessageRole, SessionManager
from municipal.core.config import LLMConfig, Settings
from municipal.llm.model_manager import (
    ModelManager,
    ModelInfo,
    LoadedModelInfo,
    ModelRecommendation,
    SystemResources,
    ModelType,
    classify_model,
)


# =========================================================================
# classify_model Tests
# =========================================================================


class TestClassifyModel:
    def test_embedding_by_family(self):
        assert classify_model("nomic-embed-text:latest", "nomic-bert") == ModelType.EMBEDDING

    def test_embedding_by_name(self):
        assert classify_model("all-minilm-l6:latest", "unknown") == ModelType.EMBEDDING
        assert classify_model("bge-large:latest", "unknown") == ModelType.EMBEDDING

    def test_vision_by_family(self):
        assert classify_model("llava:7b", "llava") == ModelType.VISION

    def test_vision_by_name(self):
        assert classify_model("llava-phi3:latest", "phi3") == ModelType.VISION

    def test_code_by_name(self):
        assert classify_model("codellama:7b", "llama") == ModelType.CODE
        assert classify_model("starcoder2:3b", "starcoder") == ModelType.CODE

    def test_text_default(self):
        assert classify_model("gemma3:4b", "gemma3") == ModelType.TEXT
        assert classify_model("qwen3:8b", "qwen3") == ModelType.TEXT
        assert classify_model("deepseek-r1:8b", "llama") == ModelType.TEXT
        assert classify_model("phi3.5:latest", "phi3") == ModelType.TEXT
from municipal.web.app import create_app


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def llm_config():
    return LLMConfig(
        provider="ollama",
        base_url="http://localhost:11434",
        model="gemma3:4b",
        context_length=4096,
        keep_alive="5m",
    )


@pytest.fixture
def model_manager(llm_config):
    return ModelManager(llm_config)


@pytest.fixture
def session_manager():
    return SessionManager()


# =========================================================================
# LLMConfig Tests
# =========================================================================


class TestLLMConfig:
    def test_default_context_length(self):
        config = LLMConfig()
        assert config.context_length == 4096

    def test_default_keep_alive(self):
        config = LLMConfig()
        assert config.keep_alive == "5m"

    def test_custom_context_length(self):
        config = LLMConfig(context_length=8192)
        assert config.context_length == 8192

    def test_custom_keep_alive(self):
        config = LLMConfig(keep_alive="-1")
        assert config.keep_alive == "-1"


# =========================================================================
# ModelManager Tests
# =========================================================================


class TestModelManager:
    @pytest.mark.asyncio
    async def test_list_available_success(self, model_manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {
                    "name": "gemma3:4b",
                    "size": 2_700_000_000,
                    "modified_at": "2025-01-01T00:00:00Z",
                    "digest": "abc123",
                    "details": {
                        "parameter_size": "4B",
                        "family": "gemma",
                        "quantization_level": "Q4_0",
                        "format": "gguf",
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(model_manager._http, "get", new_callable=AsyncMock, return_value=mock_resp):
            models = await model_manager.list_available()

        assert len(models) == 1
        assert models[0].name == "gemma3:4b"
        assert models[0].parameter_size == "4B"
        assert models[0].family == "gemma"
        assert models[0].size_gb > 0

    @pytest.mark.asyncio
    async def test_list_available_error(self, model_manager):
        with patch.object(
            model_manager._http,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            models = await model_manager.list_available()
        assert models == []

    @pytest.mark.asyncio
    async def test_list_loaded(self, model_manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {
                    "name": "gemma3:4b",
                    "size": 2_700_000_000,
                    "size_vram": 1_500_000_000,
                    "context_length": 8192,
                    "details": {},
                    "expires_at": "2025-01-01T01:00:00Z",
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(model_manager._http, "get", new_callable=AsyncMock, return_value=mock_resp):
            loaded = await model_manager.list_loaded()

        assert len(loaded) == 1
        assert loaded[0].name == "gemma3:4b"
        assert loaded[0].context_length == 8192

    @pytest.mark.asyncio
    async def test_show_model(self, model_manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "modelfile": "FROM gemma3:4b",
            "parameters": "num_ctx 4096",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(model_manager._http, "post", new_callable=AsyncMock, return_value=mock_resp):
            info = await model_manager.show_model("gemma3:4b")

        assert "modelfile" in info

    @pytest.mark.asyncio
    async def test_load_model(self, model_manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": ""}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(model_manager._http, "post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            result = await model_manager.load_model("gemma3:4b", keep_alive="-1", num_ctx=8192)

        assert result["status"] == "loaded"
        assert result["model"] == "gemma3:4b"
        call_payload = mock_post.call_args[1]["json"]
        assert call_payload["keep_alive"] == "-1"
        assert call_payload["options"]["num_ctx"] == 8192

    @pytest.mark.asyncio
    async def test_unload_model(self, model_manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": ""}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(model_manager._http, "post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            result = await model_manager.unload_model("gemma3:4b")

        assert result["status"] == "unloaded"
        call_payload = mock_post.call_args[1]["json"]
        assert call_payload["keep_alive"] == 0

    def test_get_system_resources(self):
        resources = ModelManager.get_system_resources()
        assert isinstance(resources, SystemResources)
        assert resources.cpu_count > 0
        assert resources.platform != ""

    @pytest.mark.asyncio
    async def test_recommend_models(self, model_manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {
                    "name": "tiny-model",
                    "size": 500_000_000,
                    "details": {"parameter_size": "1B", "family": "test"},
                },
                {
                    "name": "huge-model",
                    "size": 100_000_000_000,
                    "details": {"parameter_size": "70B", "family": "test"},
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(model_manager._http, "get", new_callable=AsyncMock, return_value=mock_resp):
            recs = await model_manager.recommend_models()

        assert len(recs) == 2
        # Tiny model should be first (better fit)
        assert recs[0].model.name == "tiny-model"
        assert recs[0].score >= recs[1].score

    @pytest.mark.asyncio
    async def test_close(self, model_manager):
        with patch.object(model_manager._http, "aclose", new_callable=AsyncMock) as mock_close:
            await model_manager.close()
        mock_close.assert_called_once()


# =========================================================================
# Enhanced Session Management Tests
# =========================================================================


class TestEnhancedSessionManager:
    def test_session_has_title_field(self, session_manager):
        session = session_manager.create_session()
        assert session.title is None

    def test_rename_session(self, session_manager):
        session = session_manager.create_session()
        result = session_manager.rename_session(session.session_id, "My Chat")
        assert result.title == "My Chat"

    def test_rename_session_not_found(self, session_manager):
        with pytest.raises(KeyError, match="not found"):
            session_manager.rename_session("bad-id", "Title")

    def test_delete_session(self, session_manager):
        session = session_manager.create_session()
        session_manager.delete_session(session.session_id)
        assert session_manager.get_session(session.session_id) is None

    def test_delete_session_not_found(self, session_manager):
        with pytest.raises(KeyError, match="not found"):
            session_manager.delete_session("nonexistent")

    def test_set_title_auto(self, session_manager):
        session = session_manager.create_session()
        session_manager.set_title(session.session_id, "When is recycling pickup day?")
        result = session_manager.get_session(session.session_id)
        assert result.title == "When is recycling pickup day?"

    def test_set_title_truncates_long_messages(self, session_manager):
        session = session_manager.create_session()
        long_msg = "A" * 100
        session_manager.set_title(session.session_id, long_msg)
        result = session_manager.get_session(session.session_id)
        assert len(result.title) == 50

    def test_set_title_no_overwrite(self, session_manager):
        session = session_manager.create_session()
        session_manager.set_title(session.session_id, "First title")
        session_manager.set_title(session.session_id, "Second title")
        result = session_manager.get_session(session.session_id)
        assert result.title == "First title"


# =========================================================================
# API Endpoint Tests
# =========================================================================


@pytest.fixture
def mock_rag_pipeline():
    from municipal.rag.citation import Citation, CitedAnswer
    from municipal.rag.pipeline import RAGPipeline

    pipeline = MagicMock(spec=RAGPipeline)
    pipeline.ask = AsyncMock(
        return_value=CitedAnswer(
            answer="Test answer.",
            citations=[],
            confidence=0.9,
            sources_used=0,
            low_confidence=False,
        )
    )
    return pipeline


@pytest.fixture
def mock_audit_logger(tmp_path):
    from municipal.core.config import AuditConfig
    from municipal.governance.audit import AuditLogger

    config = AuditConfig(log_dir=str(tmp_path / "audit"))
    return AuditLogger(config=config)


@pytest.fixture
def client(mock_rag_pipeline, mock_audit_logger):
    app = create_app(
        settings=Settings(),
        rag_pipeline=mock_rag_pipeline,
        audit_logger=mock_audit_logger,
    )
    return TestClient(app)


class TestSessionAPIEndpoints:
    def test_session_includes_title(self, client):
        resp = client.post("/api/sessions", json={"session_type": "anonymous"})
        data = resp.json()
        assert "title" in data
        assert data["title"] is None

    def test_rename_session(self, client):
        create_resp = client.post("/api/sessions", json={"session_type": "anonymous"})
        session_id = create_resp.json()["session_id"]

        resp = client.patch(
            f"/api/sessions/{session_id}",
            json={"title": "My Important Chat"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "My Important Chat"

    def test_rename_session_not_found(self, client):
        resp = client.patch(
            "/api/sessions/nonexistent",
            json={"title": "Title"},
        )
        assert resp.status_code == 404

    def test_delete_session(self, client):
        create_resp = client.post("/api/sessions", json={"session_type": "anonymous"})
        session_id = create_resp.json()["session_id"]

        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_session_not_found(self, client):
        resp = client.delete("/api/sessions/nonexistent")
        assert resp.status_code == 404

    def test_list_sessions_includes_title(self, client):
        create_resp = client.post("/api/sessions", json={"session_type": "anonymous"})
        session_id = create_resp.json()["session_id"]
        client.patch(f"/api/sessions/{session_id}", json={"title": "Titled Chat"})

        resp = client.get("/api/sessions")
        data = resp.json()
        titled = [s for s in data if s["session_id"] == session_id]
        assert len(titled) == 1
        assert titled[0]["title"] == "Titled Chat"

    def test_chat_auto_titles_session(self, client):
        create_resp = client.post("/api/sessions", json={"session_type": "anonymous"})
        session_id = create_resp.json()["session_id"]

        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "When is recycling?"},
        )

        get_resp = client.get(f"/api/sessions/{session_id}")
        data = get_resp.json()
        assert data["title"] == "When is recycling?"


class TestModelAPIEndpoints:
    def test_system_resources(self, client):
        resp = client.get("/api/system/resources")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_ram_gb" in data
        assert "cpu_count" in data
        assert "platform" in data

    def test_model_config_update(self, client):
        resp = client.patch(
            "/api/models/config",
            json={"context_length": 8192, "keep_alive": "-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "updated"
        assert data["config"]["context_length"] == 8192
        assert data["config"]["keep_alive"] == "-1"
