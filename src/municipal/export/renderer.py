"""Case packet renderer for JSON and PDF export."""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from municipal.export.models import CasePacket

if TYPE_CHECKING:
    from municipal.finance.models import FeeEstimate, PaymentRecord
    from municipal.review.models import CaseSummary, RedactionReport, SunshineReportData


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

    def render_summary_pdf(self, summary: CaseSummary) -> bytes:
        """Render a case summary as a PDF document."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Case Summary: {summary.case_id}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Wizard: {summary.wizard_title}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Status: {summary.status}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Classification: {summary.classification}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Created: {summary.created_at}", new_x="LMARGIN", new_y="NEXT")

        if summary.approval_status:
            pdf.cell(0, 8, f"Approval: {summary.approval_status}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)

        # Key facts
        if summary.key_facts:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Key Facts", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for key, value in summary.key_facts.items():
                label = key.replace("_", " ").title()
                pdf.cell(0, 7, f"{label}: {value}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # Related entities
        if summary.related_entities:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Related Entities", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for entity in summary.related_entities:
                pdf.cell(
                    0, 7,
                    f"{entity.get('type', '')}: {entity.get('label', '')}",
                    new_x="LMARGIN", new_y="NEXT",
                )

        return pdf.output()

    def render_redacted_pdf(self, packet: CasePacket, redaction_report: RedactionReport) -> bytes:
        """Render a case packet with redaction markers applied."""
        from fpdf import FPDF

        redacted_fields = {s.field_id for s in redaction_report.suggestions}

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"{packet.wizard_title or 'Case Packet'} [REDACTED]", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Case ID: {packet.case.id}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Status: {packet.case.status}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Application Data", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

        for key, value in packet.case.data.items():
            label = key.replace("_", " ").title()
            if key in redacted_fields:
                val_str = "[REDACTED]"
            else:
                val_str = str(value) if value is not None else ""
            pdf.cell(0, 7, f"{label}: {val_str}", new_x="LMARGIN", new_y="NEXT")

        return pdf.output()

    def render_sunshine_pdf(self, report_data: SunshineReportData) -> bytes:
        """Render a Sunshine Report as a PDF document."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, report_data.title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {report_data.generated_at.isoformat()}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Executive Summary
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Total Cases Processed: {report_data.total_cases}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        # Cases by Type
        if report_data.cases_by_type:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Cases by Type", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for wtype, count in report_data.cases_by_type.items():
                pdf.cell(0, 7, f"  {wtype}: {count}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # Cases by Status
        if report_data.cases_by_status:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Cases by Status", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for status, count in report_data.cases_by_status.items():
                pdf.cell(0, 7, f"  {status}: {count}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # Approval Statistics
        if report_data.approval_stats:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Approval Statistics", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for key, value in report_data.approval_stats.items():
                label = key.replace("_", " ").title()
                pdf.cell(0, 7, f"  {label}: {value}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # FOIA Metrics
        if report_data.foia_metrics:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "FOIA Metrics", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for key, value in report_data.foia_metrics.items():
                label = key.replace("_", " ").title()
                pdf.cell(0, 7, f"  {label}: {value}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # 311 Service Requests
        if report_data.service_311_stats:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "311 Service Requests", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for key, value in report_data.service_311_stats.items():
                label = key.replace("_", " ").title()
                pdf.cell(0, 7, f"  {label}: {value}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # Notification Summary
        if report_data.notification_summary:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Notification Summary", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for key, value in report_data.notification_summary.items():
                label = key.replace("_", " ").title()
                pdf.cell(0, 7, f"  {label}: {value}", new_x="LMARGIN", new_y="NEXT")

        return pdf.output()

    def render_fee_estimate_pdf(self, estimate: FeeEstimate) -> bytes:
        """Render a fee estimate as a PDF document."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Fee Estimate", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        if estimate.case_id:
            pdf.cell(0, 8, f"Case ID: {estimate.case_id}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Wizard Type: {estimate.wizard_type}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Computed: {estimate.computed_at.isoformat()}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Line Items", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

        for item in estimate.line_items:
            line = f"  {item.description}: ${item.subtotal:.2f}"
            if item.quantity != 1.0:
                line += f" ({item.quantity} x ${item.amount:.2f})"
            pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, f"Total: ${estimate.total:.2f}", new_x="LMARGIN", new_y="NEXT")

        return pdf.output()

    def render_payment_receipt_pdf(self, record: PaymentRecord) -> bytes:
        """Render a payment receipt as a PDF document."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Payment Receipt", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Payment ID: {record.payment_id}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Case ID: {record.case_id}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Amount: ${record.amount:.2f}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Status: {record.status.value}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Date: {record.created_at.isoformat()}", new_x="LMARGIN", new_y="NEXT")

        if record.approval_request_id:
            pdf.cell(0, 8, f"Approval ID: {record.approval_request_id}", new_x="LMARGIN", new_y="NEXT")

        return pdf.output()
