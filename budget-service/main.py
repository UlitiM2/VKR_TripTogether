"""
Сервис бюджета и расходов поездки.
- Добавление расходов (сумма, категория, кто оплатил, между кем делим).
- Список расходов по поездке.
- Расчёт долгов между участниками (упрощение переводов).
"""
from collections import defaultdict
from decimal import Decimal
import logging
import os
import uuid

import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from db.db import engine, Base, get_db
from models.expense import Expense, ExpenseShare
from schemas.expense import (
    ExpenseCreate,
    ExpenseResponse,
    DebtsSummary,
    DebtItem,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
TRIP_SERVICE_URL = os.getenv("TRIP_SERVICE_URL", "http://trip-service:8000")


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Верификация токена через Auth Service."""
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/verify",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=5.0,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def check_trip_access(
    trip_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Проверка доступа к поездке через Trip Service."""
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TRIP_SERVICE_URL}/trips/{trip_id}/internal/check-access",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Trip not found")
            if response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to access this trip",
                )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Trip service error")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Trip service unavailable")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Budget Service")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield
    logger.info("Budget Service stopped")
    engine.dispose()


app = FastAPI(
    title="TripPlanner Budget Service",
    lifespan=lifespan,
)


def _get_user_uuid(user_data: dict) -> uuid.UUID:
    user_id_str = user_data.get("user_id") or user_data.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="User ID not found in token")
    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


def _parse_uuid(value: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{name} not found")


def _compute_debts(db: Session, trip_id: uuid.UUID) -> list[DebtItem]:
    """
    По расходам поездки вычислить баланс каждого участника и упростить до
    минимального набора переводов (кто кому сколько должен).
    """
    expenses = (
        db.query(Expense)
        .filter(Expense.trip_id == trip_id)
        .all()
    )
    balance = defaultdict(lambda: Decimal("0"))
    for exp in expenses:
        shares = (
            db.query(ExpenseShare.user_id)
            .filter(ExpenseShare.expense_id == exp.id)
            .all()
        )
        share_user_ids = [s[0] for s in shares]
        n = len(share_user_ids)
        if n == 0:
            continue
        per_person = exp.amount / n
        payer = exp.paid_by_user_id
        for uid in share_user_ids:
            if uid != payer:
                balance[uid] -= per_person
                balance[payer] += per_person
    # Убираем нулевые и округляем
    balances = {
        u: float(b) for u, b in balance.items()
        if b != 0
    }
    debts_out = []
    while balances:
        debtor = min(balances, key=lambda u: balances[u])
        creditor = max(balances, key=lambda u: balances[u])
        if balances[debtor] >= 0 or balances[creditor] <= 0:
            break
        amount = min(-balances[debtor], balances[creditor])
        amount = round(amount, 2)
        if amount <= 0:
            break
        debts_out.append(
            DebtItem(from_user_id=debtor, to_user_id=creditor, amount=amount)
        )
        balances[debtor] += amount
        balances[creditor] -= amount
        if abs(balances[debtor]) < 1e-6:
            del balances[debtor]
        if abs(balances[creditor]) < 1e-6:
            del balances[creditor]
    return debts_out


@app.get("/")
async def root():
    return {
        "service": "Budget Service",
        "status": "running",
        "endpoints": {
            "add_expense": "POST /trips/{trip_id}/expenses",
            "list_expenses": "GET /trips/{trip_id}/expenses",
            "debts": "GET /trips/{trip_id}/expenses/debts",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "budget-service"}


@app.post(
    "/trips/{trip_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_expense(
    trip_id: str,
    body: ExpenseCreate,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Добавить расход. split_between — между кем делим (включая себя)."""
    user_uuid = _get_user_uuid(user_data)
    trip_uuid = _parse_uuid(trip_id, "Trip")
    payer_uuid = body.paid_by_user_id or user_uuid

    expense = Expense(
        trip_id=trip_uuid,
        paid_by_user_id=payer_uuid,
        amount=Decimal(str(body.amount)),
        category=body.category,
        description=body.description,
    )
    db.add(expense)
    db.flush()
    for uid in body.split_between:
        db.add(ExpenseShare(expense_id=expense.id, user_id=uid))
    db.commit()
    db.refresh(expense)
    share_count = len(body.split_between)
    logger.info(f"Expense {expense.id} added to trip {trip_id}, shared by {share_count}")
    return ExpenseResponse(
        id=expense.id,
        trip_id=expense.trip_id,
        paid_by_user_id=expense.paid_by_user_id,
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        created_at=expense.created_at,
        share_count=share_count,
    )


@app.get("/trips/{trip_id}/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Список расходов поездки."""
    trip_uuid = _parse_uuid(trip_id, "Trip")
    expenses = (
        db.query(Expense)
        .filter(Expense.trip_id == trip_uuid)
        .order_by(Expense.created_at.desc())
        .all()
    )
    result = []
    for exp in expenses:
        share_count = (
            db.query(ExpenseShare)
            .filter(ExpenseShare.expense_id == exp.id)
            .count()
        )
        result.append(
            ExpenseResponse(
                id=exp.id,
                trip_id=exp.trip_id,
                paid_by_user_id=exp.paid_by_user_id,
                amount=exp.amount,
                category=exp.category,
                description=exp.description,
                created_at=exp.created_at,
                share_count=share_count,
            )
        )
    return result


@app.get("/trips/{trip_id}/expenses/debts", response_model=DebtsSummary)
async def get_debts(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Расчёт долгов между участниками: минимальный набор переводов для закрытия расчётов."""
    trip_uuid = _parse_uuid(trip_id, "Trip")
    debts = _compute_debts(db, trip_uuid)
    return DebtsSummary(debts=debts)


@app.delete("/trips/{trip_id}/expenses/{expense_id}")
async def delete_expense(
    trip_id: str,
    expense_id: str,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Удалить расход. Разрешено только тому, кто оплатил расход."""
    user_uuid = _get_user_uuid(user_data)
    trip_uuid = _parse_uuid(trip_id, "Trip")
    exp_uuid = _parse_uuid(expense_id, "Expense")
    expense = (
        db.query(Expense)
        .filter(Expense.id == exp_uuid, Expense.trip_id == trip_uuid)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.paid_by_user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only expense payer can delete expense",
        )
    db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense.id).delete()
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
