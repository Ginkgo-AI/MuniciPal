"""Tests for WP4: PostgresPaymentRepository with SQLite async."""

from __future__ import annotations

import pytest

from municipal.db.base import Base
from municipal.db.engine import DatabaseManager
from municipal.finance.models import PaymentRecord, PaymentStatus
from municipal.repositories.postgres.payments import PostgresPaymentRepository

import municipal.db.models  # noqa: F401


@pytest.fixture
async def repo():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresPaymentRepository(db)
    await db.close()


async def test_save_and_get(repo):
    record = PaymentRecord(case_id="c1", amount=100.0)
    await repo.save(record)
    found = await repo.get(record.payment_id)
    assert found is not None
    assert found.amount == 100.0
    assert found.case_id == "c1"


async def test_get_for_case(repo):
    await repo.save(PaymentRecord(case_id="c1", amount=50.0))
    await repo.save(PaymentRecord(case_id="c1", amount=75.0))
    await repo.save(PaymentRecord(case_id="c2", amount=25.0))
    assert len(await repo.get_for_case("c1")) == 2


async def test_list_all(repo):
    await repo.save(PaymentRecord(case_id="c1", amount=10.0))
    assert len(await repo.list_all()) == 1


async def test_update_status(repo):
    record = PaymentRecord(case_id="c1", amount=100.0, status=PaymentStatus.PENDING)
    await repo.save(record)
    record.status = PaymentStatus.APPROVED
    await repo.save(record)
    found = await repo.get(record.payment_id)
    assert found.status == PaymentStatus.APPROVED
