"""FastAPI router for intake wizard, GIS, identity upgrade, and i18n endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

router = APIRouter()


# --- Request/Response models ---


class StartWizardResponse(BaseModel):
    state_id: str
    wizard_id: str
    current_step: str
    total_steps: int


class StepSubmitRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    session_type: str = "anonymous"


class WizardStateResponse(BaseModel):
    id: str
    wizard_id: str
    current_step_index: int
    steps: list[dict[str, Any]]
    completed: bool


class ValidateFieldRequest(BaseModel):
    wizard_id: str
    step_id: str
    field_id: str
    value: Any = None


class ValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class CaseResponse(BaseModel):
    id: str
    wizard_id: str
    session_id: str
    data: dict[str, Any]
    classification: str
    status: str
    created_at: str
    approval_request_id: str | None = None


class UpgradeRequestBody(BaseModel):
    pass


class UpgradeVerifyBody(BaseModel):
    verification_id: str
    code: str


# --- Wizard endpoints ---


@router.get("/api/intake/wizards")
async def list_wizards(request: Request) -> list[dict[str, Any]]:
    engine = request.app.state.wizard_engine
    return [
        {
            "id": defn.id,
            "title": defn.title,
            "description": defn.description,
            "steps": len(defn.steps),
        }
        for defn in engine.wizard_definitions.values()
    ]


@router.post("/api/intake/wizards/{wizard_id}/start")
async def start_wizard(
    wizard_id: str, request: Request
) -> StartWizardResponse:
    engine = request.app.state.wizard_engine
    session_manager = request.app.state.session_manager
    # Create a dedicated session for this wizard to avoid cross-user binding
    from municipal.core.types import SessionType
    auth_tier = getattr(request.state, "auth_tier", SessionType.ANONYMOUS)
    session = session_manager.create_session(auth_tier)

    try:
        state = engine.start_wizard(wizard_id, session.session_id, session.session_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StartWizardResponse(
        state_id=state.id,
        wizard_id=state.wizard_id,
        current_step=state.steps[state.current_step_index].step_id,
        total_steps=len(state.steps),
    )


@router.get("/api/intake/state/{state_id}")
async def get_wizard_state(state_id: str, request: Request) -> WizardStateResponse:
    store = request.app.state.intake_store
    state = store.get_wizard_state(state_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Wizard state {state_id!r} not found")

    return WizardStateResponse(
        id=state.id,
        wizard_id=state.wizard_id,
        current_step_index=state.current_step_index,
        steps=[
            {
                "step_id": s.step_id,
                "status": s.status.value,
                "data": s.data,
                "errors": s.errors,
            }
            for s in state.steps
        ],
        completed=state.completed,
    )


@router.post("/api/intake/state/{state_id}/steps/{step_id}")
async def submit_step(
    state_id: str, step_id: str, body: StepSubmitRequest, request: Request
) -> WizardStateResponse:
    engine = request.app.state.wizard_engine
    from municipal.core.types import SessionType
    try:
        session_type = SessionType(body.session_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid session_type: {body.session_type!r}. "
            f"Valid values: {[t.value for t in SessionType]}",
        )

    try:
        state = engine.submit_step(state_id, step_id, body.data, session_type)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return WizardStateResponse(
        id=state.id,
        wizard_id=state.wizard_id,
        current_step_index=state.current_step_index,
        steps=[
            {
                "step_id": s.step_id,
                "status": s.status.value,
                "data": s.data,
                "errors": s.errors,
            }
            for s in state.steps
        ],
        completed=state.completed,
    )


@router.post("/api/intake/state/{state_id}/back")
async def go_back(state_id: str, request: Request) -> WizardStateResponse:
    engine = request.app.state.wizard_engine
    try:
        state = engine.go_back(state_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return WizardStateResponse(
        id=state.id,
        wizard_id=state.wizard_id,
        current_step_index=state.current_step_index,
        steps=[
            {
                "step_id": s.step_id,
                "status": s.status.value,
                "data": s.data,
                "errors": s.errors,
            }
            for s in state.steps
        ],
        completed=state.completed,
    )


@router.post("/api/intake/state/{state_id}/submit")
async def submit_wizard(state_id: str, request: Request) -> CaseResponse:
    engine = request.app.state.wizard_engine
    store = request.app.state.intake_store
    state = store.get_wizard_state(state_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Wizard state {state_id!r} not found")

    try:
        case = engine.submit_wizard(state_id, state.session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CaseResponse(
        id=case.id,
        wizard_id=case.wizard_id,
        session_id=case.session_id,
        data=case.data,
        classification=case.classification.value,
        status=case.status,
        created_at=case.created_at.isoformat(),
        approval_request_id=case.approval_request_id,
    )


@router.post("/api/intake/validate")
async def validate_field(body: ValidateFieldRequest, request: Request) -> ValidationResponse:
    engine = request.app.state.wizard_engine
    validation = request.app.state.validation_engine

    defn = engine.wizard_definitions.get(body.wizard_id)
    if defn is None:
        raise HTTPException(status_code=404, detail=f"Wizard {body.wizard_id!r} not found")

    # Find the field definition
    for step in defn.steps:
        if step.id == body.step_id:
            for field in step.fields:
                if field.id == body.field_id:
                    errors = validation.validate_field(field, body.value)
                    return ValidationResponse(valid=len(errors) == 0, errors=errors)

    raise HTTPException(status_code=404, detail="Field not found")


class CrossFieldValidationResponse(BaseModel):
    valid: bool
    errors: dict[str, list[str]] = Field(default_factory=dict)


@router.post("/api/intake/state/{state_id}/validate")
async def validate_cross_field(state_id: str, request: Request) -> CrossFieldValidationResponse:
    """Run cross-field validation on a wizard state's merged data."""
    store = request.app.state.intake_store
    validation = request.app.state.validation_engine

    state = store.get_wizard_state(state_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Wizard state {state_id!r} not found")

    # Merge all step data
    merged_data: dict[str, Any] = {}
    for s in state.steps:
        merged_data.update(s.data)

    result = validation.validate_cross_field(state.wizard_id, merged_data)
    return CrossFieldValidationResponse(valid=result.valid, errors=result.errors)


# --- Case endpoints ---


@router.get("/api/intake/cases")
async def list_cases(request: Request, session_id: str | None = None) -> list[CaseResponse]:
    store = request.app.state.intake_store
    if session_id:
        cases = store.list_cases(session_id)
    else:
        cases = store.list_all_cases()

    return [
        CaseResponse(
            id=c.id,
            wizard_id=c.wizard_id,
            session_id=c.session_id,
            data=c.data,
            classification=c.classification.value,
            status=c.status,
            created_at=c.created_at.isoformat(),
            approval_request_id=c.approval_request_id,
        )
        for c in cases
    ]


@router.get("/api/intake/cases/{case_id}")
async def get_case(case_id: str, request: Request) -> CaseResponse:
    store = request.app.state.intake_store
    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    return CaseResponse(
        id=case.id,
        wizard_id=case.wizard_id,
        session_id=case.session_id,
        data=case.data,
        classification=case.classification.value,
        status=case.status,
        created_at=case.created_at.isoformat(),
        approval_request_id=case.approval_request_id,
    )


@router.get("/api/intake/cases/{case_id}/export")
async def export_case(case_id: str, request: Request, format: str = "json") -> Response:
    store = request.app.state.intake_store
    renderer = request.app.state.packet_renderer
    engine = request.app.state.wizard_engine

    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    defn = engine.wizard_definitions.get(case.wizard_id)
    from municipal.export.models import CasePacket
    packet = CasePacket(
        case=case,
        wizard_title=defn.title if defn else "",
        wizard_description=defn.description if defn else "",
    )

    if format == "pdf":
        pdf_bytes = renderer.render_pdf(packet)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=case-{case_id}.pdf"},
        )

    json_str = renderer.render_json(packet)
    return Response(content=json_str, media_type="application/json")


# --- GIS endpoints ---


@router.get("/api/gis/parcel")
async def gis_lookup_by_address(request: Request, address: str = "") -> dict[str, Any]:
    gis = request.app.state.gis_service
    if not address:
        raise HTTPException(status_code=400, detail="address query parameter is required")
    parcel = gis.lookup_by_address(address)
    if parcel is None:
        raise HTTPException(status_code=404, detail=f"No parcel found for address: {address!r}")
    return parcel.model_dump()


@router.get("/api/gis/parcel/{parcel_id}")
async def gis_lookup_by_id(parcel_id: str, request: Request) -> dict[str, Any]:
    gis = request.app.state.gis_service
    parcel = gis.lookup_by_id(parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail=f"No parcel found for ID: {parcel_id!r}")
    return parcel.model_dump()


# --- Identity upgrade endpoints ---


@router.post("/api/sessions/{session_id}/upgrade/request")
async def request_upgrade(session_id: str, request: Request) -> dict[str, Any]:
    upgrade_service = request.app.state.upgrade_service
    try:
        result = upgrade_service.request_upgrade(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/api/sessions/{session_id}/upgrade/verify")
async def verify_upgrade(
    session_id: str, body: UpgradeVerifyBody, request: Request
) -> dict[str, Any]:
    upgrade_service = request.app.state.upgrade_service
    try:
        result = upgrade_service.verify_upgrade(session_id, body.verification_id, body.code)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# --- i18n endpoints ---


@router.get("/api/i18n/locales")
async def list_locales(request: Request) -> dict[str, Any]:
    i18n = request.app.state.i18n_engine
    return {"locales": i18n.locales, "default": i18n.default_locale}


@router.get("/api/i18n/bundle/{locale}")
async def get_bundle(locale: str, request: Request) -> dict[str, Any]:
    i18n = request.app.state.i18n_engine
    bundle = i18n.get_bundle(locale)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"Locale {locale!r} not found")
    return bundle


# --- Auth endpoints ---


class AuthLoginRequest(BaseModel):
    username: str
    code: str


class AuthTokenRequest(BaseModel):
    token: str


@router.post("/api/auth/login")
async def auth_login(body: AuthLoginRequest, request: Request) -> dict[str, Any]:
    """Authenticate and get a token."""
    provider = getattr(request.app.state, "auth_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Auth provider not available")

    from municipal.auth.models import AuthCredentials
    result = provider.authenticate(AuthCredentials(username=body.username, code=body.code))
    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)
    return result.model_dump(exclude_none=False)


@router.post("/api/auth/validate")
async def auth_validate(body: AuthTokenRequest, request: Request) -> dict[str, Any]:
    """Validate a token."""
    provider = getattr(request.app.state, "auth_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Auth provider not available")

    validation = provider.validate_token(body.token)
    return validation.model_dump(mode="json")


@router.post("/api/auth/refresh")
async def auth_refresh(body: AuthTokenRequest, request: Request) -> dict[str, Any]:
    """Refresh a token."""
    provider = getattr(request.app.state, "auth_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Auth provider not available")

    result = provider.refresh_token(body.token)
    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)
    return result.model_dump(exclude_none=False)


@router.post("/api/auth/logout")
async def auth_logout(body: AuthTokenRequest, request: Request) -> dict[str, Any]:
    """Revoke a token."""
    provider = getattr(request.app.state, "auth_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Auth provider not available")

    revoked = provider.revoke_token(body.token)
    return {"revoked": revoked}
