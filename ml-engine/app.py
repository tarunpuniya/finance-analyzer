import os
import pickle
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # ml-engine folder

# ── Valid categories (data.py ke saath sync) ─────────────────────────────────
VALID_CATEGORIES = [
    "Groceries", "Food", "Rent", "Shopping", "Travel",
    "Medical", "Entertainment", "Investment", "Bills",
]

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Finance Safe Spending Limit API",
    description=(
        "FastAPI backend for predicting user's safe monthly spending limit "
        "using Machine Learning (Random Forest / Gradient Boosting)."
    ),
    version="2.1",
)

# ── Model load ────────────────────────────────────────────────────────────────
try:
    model = pickle.load(open(os.path.join(BASE_DIR, "finance_model.pkl"), "rb"))
    model_columns = pickle.load(open(os.path.join(BASE_DIR, "model_columns.pkl"), "rb"))
    print("[OK] Model and columns loaded successfully!")
except Exception as e:
    print(f"[ERROR] Could not load model files: {e}")
    model = None
    model_columns = None


class FinanceInput(BaseModel):
    month: int = Field(default=1, ge=1, le=12, description="Month of the year (1-12)")
    category: str = Field(
        default="Food",
        description=f"Expense category. One of: {', '.join(VALID_CATEGORIES)}",
    )
    monthly_income: float = Field(default=1000.0, ge=0, description="User's monthly income")
    prev_month_expense: float = Field(
        default=0.0, ge=0, description="Previous month's total expense"
    )

    @validator("category", pre=True, always=True)
    def sanitize_category(cls, v):
        if not v or not isinstance(v, str):
            return "Food"
        v_clean = v.strip().capitalize()
        for valid in VALID_CATEGORIES:
            if valid.lower() == v_clean.lower():
                return valid
        return "Food"

    @validator("monthly_income", pre=True, always=True)
    def sanitize_income(cls, v):
        try:
            val = float(v)
            if val <= 0:
                raise ValueError("monthly_income must be greater than 0")
            return val
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid monthly_income value")

    @validator("prev_month_expense", pre=True, always=True)
    def sanitize_expense(cls, v):
        try:
            val = float(v)
            return val if val >= 0 else 0.0
        except Exception:
            return 0.0


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return {
        "message": "Welcome to AI Finance ML Engine (FastAPI)",
        "version": "2.1",
        "docs_url": "/docs",
        "valid_categories": VALID_CATEGORIES,
    }


@app.post("/predict")
def predict_safe_limit(data: FinanceInput):
    if model is None or model_columns is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please train the model first (run train.py).",
        )

    try:
        # 1. savings_rate aur expense_ratio auto-calculate karein
        savings_rate = round(
            (data.monthly_income - data.prev_month_expense) / data.monthly_income, 4
        )
        expense_ratio = round(data.prev_month_expense / data.monthly_income, 4)

        # 2. DataFrame banao
        df = pd.DataFrame([{
            "month": data.month,
            "category": data.category,
            "monthly_income": data.monthly_income,
            "prev_month_expense": data.prev_month_expense,
            "savings_rate": savings_rate,
            "expense_ratio": expense_ratio,
        }])

        # 3. Feature engineering — bilkul train.py jaisi
        df["income_bracket"] = pd.cut(
            df["monthly_income"],
            bins=[0, 25000, 50000, 100000, 200000, float("inf")],
            labels=[1, 2, 3, 4, 5],
        ).astype(int)

        df["is_festival_month"] = df["month"].isin([10, 11, 12]).astype(int)
        df["is_tax_saving_month"] = df["month"].isin([1, 2, 3]).astype(int)

        # 4. One-hot encode category
        df = pd.get_dummies(df, columns=["category"], prefix="category")

        # 5. Missing columns ko 0 se fill karo
        for col in model_columns:
            if col not in df.columns:
                df[col] = 0

        # 6. Exact column order maintain karo
        df = df[model_columns]

        # 7. Prediction
        prediction = model.predict(df)
        safe_limit = float(prediction[0])

        return {
            "status": "success",
            "monthly_income": data.monthly_income,
            "prev_month_expense": data.prev_month_expense,
            "savings_rate": savings_rate,
            "expense_ratio": expense_ratio,
            "safe_spending_limit": round(safe_limit, 2),
            "safe_limit_percentage": round(
                (safe_limit / data.monthly_income) * 100, 2
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
