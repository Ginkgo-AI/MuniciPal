"""PostgreSQL payment repository."""

from __future__ import annotations

from sqlalchemy import select

from municipal.core.types import DataClassification
from municipal.db.engine import DatabaseManager
from municipal.db.models import PaymentRecordRow
from municipal.finance.models import PaymentRecord, PaymentStatus


class PostgresPaymentRepository:
    """Postgres-backed payment record storage."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def save(self, record: PaymentRecord) -> PaymentRecord:
        async with self._db.session() as db:
            existing = await db.get(PaymentRecordRow, record.payment_id)
            if existing:
                existing.case_id = record.case_id
                existing.amount = record.amount
                existing.status = record.status.value
                existing.approval_request_id = record.approval_request_id
                existing.classification = record.classification.value
                existing.updated_at = record.updated_at
            else:
                row = PaymentRecordRow(
                    payment_id=record.payment_id,
                    case_id=record.case_id,
                    amount=record.amount,
                    status=record.status.value,
                    approval_request_id=record.approval_request_id,
                    classification=record.classification.value,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
                db.add(row)
            await db.commit()
        return record

    async def get(self, payment_id: str) -> PaymentRecord | None:
        async with self._db.session() as db:
            row = await db.get(PaymentRecordRow, payment_id)
            if row is None:
                return None
            return self._row_to_record(row)

    async def get_for_case(self, case_id: str) -> list[PaymentRecord]:
        async with self._db.session() as db:
            result = await db.execute(
                select(PaymentRecordRow).where(PaymentRecordRow.case_id == case_id)
            )
            return [self._row_to_record(r) for r in result.scalars().all()]

    async def list_all(self) -> list[PaymentRecord]:
        async with self._db.session() as db:
            result = await db.execute(select(PaymentRecordRow))
            return [self._row_to_record(r) for r in result.scalars().all()]

    @staticmethod
    def _row_to_record(row: PaymentRecordRow) -> PaymentRecord:
        return PaymentRecord(
            payment_id=row.payment_id,
            case_id=row.case_id,
            amount=row.amount,
            status=PaymentStatus(row.status),
            approval_request_id=row.approval_request_id,
            classification=DataClassification(row.classification),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
