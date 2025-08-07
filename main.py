from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import List

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from models import Balance, Payout, Transaction

app = FastAPI(title="Payments API")

# In-memory storage for demo purposes
transactions: List[Transaction] = [
    Transaction(id=1, user="alice@example.com", amount=100.0, description="Sale", created_at=datetime.utcnow()),
    Transaction(id=2, user="bob@example.com", amount=50.0, description="Sale", created_at=datetime.utcnow()),
]

payouts: List[Payout] = [
    Payout(id=1, transaction_id=1, amount=30.0),
    Payout(id=2, transaction_id=2, amount=50.0),
]

ADMIN_TOKEN = "secret"


def mask_user(user: str) -> str:
    """Hide part of the user's identity."""
    if "@" in user:
        name, domain = user.split("@", 1)
        return f"{name[0]}***@{domain}"
    return user[0] + "***"


def mask_transaction(t: Transaction) -> dict:
    d = t.dict()
    d["user"] = mask_user(t.user)
    return d


def admin_required(x_token: str = Header(...)):
    if x_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token required")


@app.get("/balance", response_model=Balance)
def get_balance() -> Balance:
    total = sum(t.amount for t in transactions)
    confirmed = sum(p.amount for p in payouts if p.status == "confirmed")
    pending = sum(p.amount for p in payouts if p.status != "confirmed")
    available = total - confirmed - pending
    return Balance(available=available, pending=pending)


@app.get("/payouts")
def list_payouts():
    history = []
    for p in payouts:
        t = next((t for t in transactions if t.id == p.transaction_id), None)
        user = mask_user(t.user) if t else ""
        history.append({**p.dict(), "user": user})
    return history


@app.post("/invoices", response_model=Transaction)
def create_invoice(tx: Transaction) -> Transaction:
    tx.id = len(transactions) + 1
    transactions.append(tx)
    return Transaction(
        id=tx.id,
        user=mask_user(tx.user),
        amount=tx.amount,
        description=tx.description,
        created_at=tx.created_at,
    )


@app.get("/admin/payouts")
def admin_payouts(token: str = Depends(admin_required)) -> List[Payout]:
    return payouts


@app.post("/admin/payouts/{payout_id}/confirm")
def confirm_payout(payout_id: int, token: str = Depends(admin_required)):
    for p in payouts:
        if p.id == payout_id:
            p.status = "confirmed"
            return {"status": "confirmed", "payout_id": payout_id}
    raise HTTPException(status_code=404, detail="Payout not found")


@app.get("/export/{data_type}.{file_type}")
def export(data_type: str, file_type: str):
    if data_type == "transactions":
        data = [mask_transaction(t) for t in transactions]
    elif data_type == "payouts":
        data = []
        for p in payouts:
            t = next((t for t in transactions if t.id == p.transaction_id), None)
            user = mask_user(t.user) if t else ""
            data.append({**p.dict(), "user": user})
    else:
        raise HTTPException(status_code=404, detail="Unknown data type")

    df = pd.DataFrame(data)
    suffix = ".csv" if file_type == "csv" else ".xlsx"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        if file_type == "csv":
            df.to_csv(tmp.name, index=False)
        elif file_type in {"xls", "xlsx"}:
            df.to_excel(tmp.name, index=False)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        return FileResponse(tmp.name, filename=f"{data_type}{suffix}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
