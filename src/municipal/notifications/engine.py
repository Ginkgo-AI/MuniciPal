"""Notification engine with template rendering and event-driven notifications."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from municipal.core.types import AuditEvent, DataClassification
from municipal.governance.audit import AuditLogger
from municipal.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationTemplate,
)
from municipal.notifications.service import NotificationService

_DEFAULT_TEMPLATES_PATH = Path(__file__).resolve().parents[3] / "config" / "notification_templates.yml"


class NotificationEngine:
    """High-level notification engine with template rendering and audit logging."""

    def __init__(
        self,
        service: NotificationService,
        audit_logger: AuditLogger | None = None,
        templates_path: str | Path | None = None,
    ) -> None:
        self._service = service
        self._audit = audit_logger
        self._templates: dict[str, NotificationTemplate] = {}
        self._load_templates(Path(templates_path) if templates_path else _DEFAULT_TEMPLATES_PATH)

    def _load_templates(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        for tmpl_id, tmpl_data in data.get("templates", {}).items():
            self._templates[tmpl_id] = NotificationTemplate(
                id=tmpl_id,
                subject=tmpl_data.get("subject", ""),
                body=tmpl_data.get("body", ""),
                channel=NotificationChannel(tmpl_data.get("channel", "email")),
            )

    @property
    def templates(self) -> dict[str, NotificationTemplate]:
        return dict(self._templates)

    def notify_case_update(
        self,
        template_id: str,
        session_id: str,
        recipient: str,
        context: dict[str, Any] | None = None,
    ) -> Notification:
        """Send a case-related notification using a template."""
        return self._send_from_template(template_id, session_id, recipient, context)

    def notify_approval_decision(
        self,
        approved: bool,
        session_id: str,
        recipient: str,
        context: dict[str, Any] | None = None,
    ) -> Notification:
        """Send an approval/denial notification."""
        template_id = "case_approved" if approved else "case_denied"
        return self._send_from_template(template_id, session_id, recipient, context)

    def send_direct(
        self,
        session_id: str,
        recipient: str,
        subject: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> Notification:
        """Send a notification directly without a template."""
        notification = Notification(
            session_id=session_id,
            recipient=recipient,
            subject=subject,
            body=body,
            channel=channel,
            priority=priority,
        )
        result = self._service.send(notification)
        self._log_audit(session_id, "notification_sent", result)
        return result

    def _send_from_template(
        self,
        template_id: str,
        session_id: str,
        recipient: str,
        context: dict[str, Any] | None = None,
    ) -> Notification:
        context = context or {}
        template = self._templates.get(template_id)

        if template:
            subject = self._render(template.subject, context)
            body = self._render(template.body, context)
            channel = template.channel
        else:
            subject = template_id.replace("_", " ").title()
            body = f"Notification: {template_id}"
            channel = NotificationChannel.EMAIL

        notification = Notification(
            session_id=session_id,
            recipient=recipient,
            subject=subject,
            body=body,
            channel=channel,
            template_id=template_id,
            metadata=context,
        )
        result = self._service.send(notification)
        self._log_audit(session_id, "notification_sent", result)
        return result

    def _render(self, template_str: str, context: dict[str, Any]) -> str:
        """Simple template rendering with {key} substitution.

        Uses a single-pass regex replacement to avoid double-substitution
        (where a substituted value could itself contain a {placeholder}).
        Unrecognised placeholders are preserved in the output.
        """
        import re
        str_context = {k: str(v) for k, v in context.items()}
        def _replace(m: re.Match) -> str:
            key = m.group(1)
            return str_context.get(key, m.group(0))
        return re.sub(r"\{(\w+)\}", _replace, template_str)

    def _log_audit(self, session_id: str, action: str, notification: Notification) -> None:
        if self._audit is None:
            return
        event = AuditEvent(
            session_id=session_id,
            actor="notification_engine",
            action=action,
            resource=f"notification:{notification.id}",
            classification=DataClassification.INTERNAL,
            details={
                "template_id": notification.template_id,
                "channel": notification.channel,
                "recipient": notification.recipient,
                "status": notification.status,
            },
        )
        self._audit.log(event)
