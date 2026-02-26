"""Tests for case export renderer."""

from __future__ import annotations

import json

import pytest

from municipal.export.models import CasePacket
from municipal.export.renderer import PacketRenderer
from municipal.intake.models import Case


@pytest.fixture
def renderer():
    return PacketRenderer()


@pytest.fixture
def sample_case():
    return Case(
        wizard_id="permit_application",
        session_id="session-1",
        data={
            "property_address": "123 Main St",
            "permit_type": "Building",
            "project_description": "New deck",
            "estimated_cost": "5000",
        },
        status="submitted",
    )


@pytest.fixture
def sample_packet(sample_case):
    return CasePacket(
        case=sample_case,
        wizard_title="Permit Application",
        wizard_description="Apply for a building permit.",
    )


class TestPacketRenderer:
    def test_render_json(self, renderer, sample_packet):
        output = renderer.render_json(sample_packet)
        data = json.loads(output)
        assert data["wizard_title"] == "Permit Application"
        assert data["case"]["wizard_id"] == "permit_application"
        assert data["case"]["data"]["property_address"] == "123 Main St"

    def test_render_pdf(self, renderer, sample_packet):
        pdf_bytes = renderer.render_pdf(sample_packet)
        assert isinstance(pdf_bytes, (bytes, bytearray))
        assert len(pdf_bytes) > 100
        # PDF files start with %PDF
        assert pdf_bytes[:5] == b"%PDF-"

    def test_render_pdf_has_fonts(self, renderer, sample_packet):
        pdf_bytes = renderer.render_pdf(sample_packet)
        # PDF should reference Helvetica font used for rendering
        assert b"Helvetica" in pdf_bytes
