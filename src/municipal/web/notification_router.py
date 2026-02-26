"""FastAPI router for notification endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from municipal.notifications.models import NotificationChannel, NotificationPriority

router = APIRouter()


class SendNotificationRequest(BaseModel):
    session_id: str
    recipient: str
    subject: str
    body: str
    channel: str = "email"
    priority: str = "normal"
    template_id: str | None = None
    context: dict[str, Any] | None = None


@router.post("/api/notifications/send")
async def send_notification(body: SendNotificationRequest, request: Request) -> dict[str, Any]:
    """Send a notification."""
    engine = getattr(request.app.state, "notification_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Notification engine not available")

    if body.template_id:
        notification = engine.notify_case_update(
            template_id=body.template_id,
            session_id=body.session_id,
            recipient=body.recipient,
            context=body.context,
        )
    else:
        notification = engine.send_direct(
            session_id=body.session_id,
            recipient=body.recipient,
            subject=body.subject,
            body=body.body,
            channel=NotificationChannel(body.channel),
            priority=NotificationPriority(body.priority),
        )

    return {
        "id": notification.id,
        "status": notification.status,
        "channel": notification.channel,
        "recipient": notification.recipient,
        "subject": notification.subject,
    }


@router.get("/api/notifications/{notification_id}")
async def get_notification(notification_id: str, request: Request) -> dict[str, Any]:
    """Get notification status."""
    service = getattr(request.app.state, "notification_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Notification service not available")

    status = service.get_status(notification_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id!r} not found")
    return {"id": notification_id, "status": status}


@router.get("/api/notifications")
async def list_notifications(
    request: Request,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """List notifications for a session."""
    service = getattr(request.app.state, "notification_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Notification service not available")

    if session_id:
        notifications = service.list_for_session(session_id)
    else:
        notifications = service.store.list_all()

    return [
        {
            "id": n.id,
            "session_id": n.session_id,
            "channel": n.channel,
            "recipient": n.recipient,
            "subject": n.subject,
            "status": n.status,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]
