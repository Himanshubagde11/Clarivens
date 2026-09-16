"""
Payment Service for Clarivens.
Explicitly demarcates development simulation vs production processing.
"""
from typing import Dict, Any
from backend.config import settings

PAYMENT_MODE = "mock"
DEV_WARNING_BANNER = "⚠️ DEVELOPMENT MOCK — NOT REAL PAYMENT PROCESSING"

PACKAGES = {
    "essential": {
        "name": "Essential Analytics",
        "price": 499,
        "features": ["Data cleaning", "EDA", "KPI analysis", "Executive summary"]
    },
    "business": {
        "name": "Business Intelligence",
        "price": 999,
        "features": ["Everything in Essential", "Interactive dashboard", "Business insights"]
    },
    "predictive": {
        "name": "Predictive Analytics",
        "price": 1499,
        "features": ["Everything in Business", "Forecasting", "Predictive modeling", "AI recommendations"]
    }
}

def create_checkout_session(package_id: str, user_id: int) -> Dict[str, Any]:
    """
    Creates a simulated development checkout session.
    Clearly marks simulation flag to prevent accidental production reliance.
    """
    if package_id not in PACKAGES:
        return {"error": "Invalid package", "error_code": "INVALID_PACKAGE"}
        
    return {
        "mode": PAYMENT_MODE,
        "notice": DEV_WARNING_BANNER,
        "checkout_url": f"/mock-payment?pkg={package_id}&user={user_id}&status=simulated",
        "amount": PACKAGES[package_id]["price"],
        "currency": "USD",
        "package_name": PACKAGES[package_id]["name"]
    }

def verify_payment(transaction_id: str) -> bool:
    """
    Validates simulated payment transactions.
    Real payment webhooks with Stripe/Razorpay require cryptographic signature validation.
    """
    if not transaction_id:
        return False
    return transaction_id.startswith("mock_txn_")
