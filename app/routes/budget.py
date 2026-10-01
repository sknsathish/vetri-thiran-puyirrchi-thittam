from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models import Budget, Expense, User, get_db
from app.routes.auth import current_user

router = APIRouter(prefix="/api", tags=["budget"])


class BudgetIn(BaseModel):
    category: str
    limit: float = Field(gt=0)


class ExpenseIn(BaseModel):
    category: str
    title: str
    amount: float = Field(gt=0)


def build_summary(db: Session, user_id: int):
    rows = []
    for b in db.query(Budget).filter_by(user_id=user_id).all():
        spent = sum(e.amount for e in db.query(Expense).filter_by(user_id=user_id, category=b.category))
        rows.append({"category": b.category, "limit": b.limit, "spent": spent,
                     "remaining": b.limit - spent, "pct": round(spent / b.limit * 100, 1)})
    return rows


@router.post("/budgets")
def set_budget(data: BudgetIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = db.query(Budget).filter_by(user_id=user.id, category=data.category).first()
    if b:
        b.limit = data.limit
    else:
        db.add(Budget(user_id=user.id, category=data.category, limit=data.limit))
    db.commit()
    return {"ok": True}


@router.post("/expenses")
def add_expense(data: ExpenseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(Expense(user_id=user.id, **data.model_dump()))
    db.commit()
    return {"ok": True}


@router.get("/expenses")
def list_expenses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Expense).filter_by(user_id=user.id).order_by(Expense.created_at.desc()).limit(50)
    return [{"id": e.id, "category": e.category, "title": e.title, "amount": e.amount} for e in q]


@router.delete("/expenses/{eid}")
def delete_expense(eid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    e = db.query(Expense).filter_by(id=eid, user_id=user.id).first()
    if not e:
        raise HTTPException(404, "Expense not found")
    db.delete(e); db.commit()
    return {"ok": True}


@router.get("/summary")
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return build_summary(db, user.id)
