"""Authentication strategy definitions for Munici-Pal.

This module defines the three resident session tiers as Pydantic models,
per Decision Log entry #4 in REFERENCE.md:

  1. Anonymous   - No identity verification; public info only.
  2. Verified    - Identity confirmed via email/phone; can view own case data.
  3. Authenticated - Full identity assurance; can initiate transactions.

This is a strategy/config document expressed as code, not a full auth
implementation. It defines what each tier *can do* and how to upgrade
between tiers.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from municipal.core.types import DataClassification


class SessionTier(StrEnum):
    """The three session tiers supported by the platform."""

    ANONYMOUS = "anonymous"
    VERIFIED = "verified"
    AUTHENTICATED = "authenticated"


class Capability(BaseModel):
    """A single capability granted to a session tier."""

    name: str
    description: str


class UpgradePath(BaseModel):
    """Defines how a session can upgrade to a higher tier."""

    target_tier: SessionTier
    method: str
    description: str


class SessionTierDefinition(BaseModel):
    """Full definition of a session tier including capabilities and upgrade paths."""

    tier: SessionTier
    label: str
    description: str
    max_classification: DataClassification
    capabilities: list[Capability] = Field(default_factory=list)
    upgrade_paths: list[UpgradePath] = Field(default_factory=list)
    can_initiate_transactions: bool = False
    can_view_pii: bool = False
    can_submit_applications: bool = False
    session_timeout_minutes: int = 30


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

AnonymousSession = SessionTierDefinition(
    tier=SessionTier.ANONYMOUS,
    label="Anonymous",
    description=(
        "No identity verification. Can browse public information, ask general "
        "questions about ordinances and fees, and get process guidance."
    ),
    max_classification=DataClassification.PUBLIC,
    capabilities=[
        Capability(
            name="browse_public_info",
            description="View published ordinances, fee schedules, FAQs, and meeting minutes.",
        ),
        Capability(
            name="ask_general_questions",
            description="Ask questions that can be answered from public knowledge base.",
        ),
        Capability(
            name="view_process_guidance",
            description="Get step-by-step guidance on municipal processes.",
        ),
        Capability(
            name="search_public_records",
            description="Search publicly available records and documents.",
        ),
    ],
    upgrade_paths=[
        UpgradePath(
            target_tier=SessionTier.VERIFIED,
            method="email_or_phone_verification",
            description=(
                "Provide an email or phone number and confirm via one-time code. "
                "Enables access to case-specific data."
            ),
        ),
    ],
    can_initiate_transactions=False,
    can_view_pii=False,
    can_submit_applications=False,
    session_timeout_minutes=30,
)

VerifiedSession = SessionTierDefinition(
    tier=SessionTier.VERIFIED,
    label="Verified",
    description=(
        "Identity confirmed via email or phone. Can view own case data, check "
        "permit status, and receive notifications."
    ),
    max_classification=DataClassification.SENSITIVE,
    capabilities=[
        Capability(
            name="browse_public_info",
            description="All anonymous capabilities.",
        ),
        Capability(
            name="view_own_cases",
            description="View status and details of own permits, complaints, and requests.",
        ),
        Capability(
            name="receive_notifications",
            description="Receive status updates via email or SMS.",
        ),
        Capability(
            name="upload_documents",
            description="Upload supporting documents for existing cases.",
        ),
    ],
    upgrade_paths=[
        UpgradePath(
            target_tier=SessionTier.AUTHENTICATED,
            method="government_id_verification",
            description=(
                "Verify identity via government-issued ID (e.g. login.gov, "
                "state ID portal). Enables initiating financial transactions "
                "and submitting new applications."
            ),
        ),
    ],
    can_initiate_transactions=False,
    can_view_pii=True,
    can_submit_applications=False,
    session_timeout_minutes=60,
)

AuthenticatedSession = SessionTierDefinition(
    tier=SessionTier.AUTHENTICATED,
    label="Authenticated",
    description=(
        "Full identity assurance via government ID. Can initiate transactions, "
        "submit applications, request records, and authorize payments."
    ),
    max_classification=DataClassification.SENSITIVE,
    capabilities=[
        Capability(
            name="browse_public_info",
            description="All anonymous and verified capabilities.",
        ),
        Capability(
            name="view_own_cases",
            description="All verified capabilities.",
        ),
        Capability(
            name="submit_applications",
            description="Submit new permit applications, complaints, and service requests.",
        ),
        Capability(
            name="initiate_payments",
            description="Pay fees, fines, and taxes online.",
        ),
        Capability(
            name="request_records",
            description="Submit FOIA and public records requests.",
        ),
        Capability(
            name="authorize_actions",
            description="Authorize actions on own property or cases.",
        ),
    ],
    upgrade_paths=[],  # Highest tier
    can_initiate_transactions=True,
    can_view_pii=True,
    can_submit_applications=True,
    session_timeout_minutes=120,
)

# Ordered list of all tier definitions for programmatic access
ALL_TIERS: list[SessionTierDefinition] = [
    AnonymousSession,
    VerifiedSession,
    AuthenticatedSession,
]


def get_tier_definition(tier: SessionTier | str) -> SessionTierDefinition:
    """Look up a session tier definition by tier value.

    Args:
        tier: A SessionTier enum or its string value.

    Returns:
        The matching SessionTierDefinition.

    Raises:
        ValueError: If the tier is not recognized.
    """
    tier_val = SessionTier(tier) if isinstance(tier, str) else tier
    for defn in ALL_TIERS:
        if defn.tier == tier_val:
            return defn
    raise ValueError(f"Unknown session tier: {tier}")
