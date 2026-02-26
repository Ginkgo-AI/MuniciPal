"""Application configuration loaded from environment and config files."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM provider configuration."""

    model_config = {"env_prefix": "MUNICIPAL_LLM_"}

    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    timeout_seconds: int = 30
    max_retries: int = 1


class VectorDBConfig(BaseSettings):
    """Vector database configuration."""

    model_config = {"env_prefix": "MUNICIPAL_VECTORDB_"}

    provider: str = "chromadb"
    host: str = "localhost"
    port: int = 8000
    collection_prefix: str = "municipal"


class AuditConfig(BaseSettings):
    """Audit logging configuration."""

    model_config = {"env_prefix": "MUNICIPAL_AUDIT_"}

    log_dir: str = "data/audit"
    hash_algorithm: str = "sha256"
    secondary_location: str | None = None


class EvalConfig(BaseSettings):
    """Evaluation harness configuration."""

    model_config = {"env_prefix": "MUNICIPAL_EVAL_"}

    golden_dataset_dir: str = "eval/golden_datasets"
    accuracy_target: float = 0.90
    citation_precision_target: float = 0.95
    citation_recall_target: float = 0.85
    hallucination_max: float = 0.05
    refusal_rate_target: float = 0.90
    latency_p50_target_ms: float = 3000.0
    latency_p95_target_ms: float = 8000.0


class IntakeConfig(BaseSettings):
    """Intake wizard configuration."""

    model_config = {"env_prefix": "MUNICIPAL_INTAKE_"}

    wizards_dir: str = "config/wizards"


class GISConfig(BaseSettings):
    """GIS service configuration."""

    model_config = {"env_prefix": "MUNICIPAL_GIS_"}

    provider: str = "mock"


class I18nConfig(BaseSettings):
    """Internationalization configuration."""

    model_config = {"env_prefix": "MUNICIPAL_I18N_"}

    bundles_dir: str = "config/i18n"
    default_locale: str = "en"


class BridgeConfig(BaseSettings):
    """Bridge adapter configuration."""

    model_config = {"env_prefix": "MUNICIPAL_BRIDGE_"}

    config_path: str = "config/bridge_adapters.yml"
    default_timeout_seconds: int = 30


class NotificationConfig(BaseSettings):
    """Notification engine configuration."""

    model_config = {"env_prefix": "MUNICIPAL_NOTIFICATION_"}

    templates_path: str = "config/notification_templates.yml"
    default_channel: str = "email"


class AuthConfig(BaseSettings):
    """Authentication configuration."""

    model_config = {"env_prefix": "MUNICIPAL_AUTH_"}

    provider: str = "mock"
    fixtures_path: str = "config/auth_fixtures.yml"
    token_expiry_minutes: int = 60


class Settings(BaseSettings):
    """Root application settings."""

    model_config = {"env_prefix": "MUNICIPAL_"}

    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    llm: LLMConfig = Field(default_factory=LLMConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    eval: EvalConfig = Field(default_factory=EvalConfig)
    intake: IntakeConfig = Field(default_factory=IntakeConfig)
    gis: GISConfig = Field(default_factory=GISConfig)
    i18n: I18nConfig = Field(default_factory=I18nConfig)
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
