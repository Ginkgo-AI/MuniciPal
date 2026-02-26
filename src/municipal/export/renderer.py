"""Case packet renderer for JSON and PDF export."""

from __future__ import annotations

import json
from typing import Any

from municipal.export.models import CasePacket


class PacketRenderer:
    """Renders case packets in JSON and PDF formats."""

    def render_json(self, packet: CasePacket) -> str:
        return packet.model_dump_json(indent=2)

    def render_pdf(self, packet: CasePacket) -> bytes:
        """Render a case packet as a PDF document using fpdf2."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, packet.wizard_title or "Case Packet", new_x="LMARGIN", new_y="NEXT")

        # Case metadata
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Case ID: {packet.case.id}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Status: {packet.case.status}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(
            0, 8,
            f"Created: {packet.case.created_at.isoformat()}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.cell(
            0, 8,
            f"Classification: {packet.case.classification}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(5)

        if packet.wizard_description:
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 6, packet.wizard_description)
            pdf.ln(5)

        # Case data
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Application Data", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

        for key, value in packet.case.data.items():
            label = key.replace("_", " ").title()
            val_str = str(value) if value is not None else ""
            pdf.cell(0, 7, f"{label}: {val_str}", new_x="LMARGIN", new_y="NEXT")

        return pdf.output()
