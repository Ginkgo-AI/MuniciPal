"""FastAPI router for review endpoints: redaction, inconsistency, summary, report, sunshine."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()


@router.post("/api/review/redact/{case_id}")
async def redact_case(case_id: str, request: Request) -> dict[str, Any]:
    """Get redaction suggestions for a case."""
    store = request.app.state.intake_store
    redaction_engine = getattr(request.app.state, "redaction_engine", None)
    wizard_engine = request.app.state.wizard_engine

    if redaction_engine is None:
        raise HTTPException(status_code=503, detail="Redaction engine not available")

    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    # Build field classifications from wizard definition
    field_classifications: dict[str, str] = {}
    defn = wizard_engine.wizard_definitions.get(case.wizard_id)
    if defn:
        for step in defn.steps:
            for field in step.fields:
                field_classifications[field.id] = field.classification.value

    report = redaction_engine.scan(
        case_id=case_id,
        data=case.data,
        field_classifications=field_classifications,
    )
    return report.model_dump(mode="json")


@router.post("/api/review/inconsistencies/{case_id}")
async def detect_inconsistencies(case_id: str, request: Request) -> dict[str, Any]:
    """Detect inconsistencies in a case's data."""
    store = request.app.state.intake_store
    detector = getattr(request.app.state, "inconsistency_detector", None)

    if detector is None:
        raise HTTPException(status_code=503, detail="Inconsistency detector not available")

    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    report = detector.detect(
        case_id=case_id,
        wizard_id=case.wizard_id,
        data=case.data,
    )
    return report.model_dump(mode="json")


@router.get("/api/review/summary/{case_id}")
async def get_case_summary(case_id: str, request: Request) -> dict[str, Any]:
    """Get a structured summary of a case."""
    store = request.app.state.intake_store
    summary_engine = getattr(request.app.state, "summary_engine", None)

    if summary_engine is None:
        raise HTTPException(status_code=503, detail="Summary engine not available")

    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    summary = summary_engine.summarize_case(case)
    return summary.model_dump(mode="json")


@router.get("/api/review/report")
async def get_department_report(
    request: Request,
    wizard_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Generate a department aggregate report."""
    summary_engine = getattr(request.app.state, "summary_engine", None)

    if summary_engine is None:
        raise HTTPException(status_code=503, detail="Summary engine not available")

    report = summary_engine.generate_department_report(
        wizard_type=wizard_type,
        date_from=date_from,
        date_to=date_to,
    )
    return report.model_dump(mode="json")


@router.get("/api/review/sunshine")
async def get_sunshine_report(request: Request) -> dict[str, Any]:
    """Generate the Sunshine Report (JSON)."""
    generator = getattr(request.app.state, "sunshine_generator", None)

    if generator is None:
        raise HTTPException(status_code=503, detail="Sunshine report generator not available")

    report = generator.generate()
    return report.model_dump(mode="json")


@router.get("/api/review/sunshine/pdf")
async def get_sunshine_report_pdf(request: Request) -> Response:
    """Generate the Sunshine Report as PDF."""
    generator = getattr(request.app.state, "sunshine_generator", None)
    renderer = request.app.state.packet_renderer

    if generator is None:
        raise HTTPException(status_code=503, detail="Sunshine report generator not available")

    report = generator.generate()
    pdf_bytes = bytes(renderer.render_sunshine_pdf(report))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sunshine-report.pdf"},
    )
