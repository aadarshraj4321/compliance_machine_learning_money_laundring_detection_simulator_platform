from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import Transaction, User
from datetime import datetime, timedelta

# --- RULE 1: Detects a user SENDING multiple small payments ---
def check_structuring_by_payment(db: Session, user: User, amount_threshold: float = 50000.0, time_window_hours: int = 48, min_transactions: int = 4) -> str | None:
    """
    Flags a user for SENDING multiple payments just under the threshold.
    This is a strong signal of intent to structure funds.
    """
    window_start_time = datetime.now() - timedelta(hours=time_window_hours)
    
    suspicious_transactions = db.query(Transaction).filter(
        and_(
            Transaction.from_user_id == user.id, # The user is the SENDER
            Transaction.timestamp >= window_start_time,
            Transaction.amount < amount_threshold,
            Transaction.amount > amount_threshold * 0.8
        )
    ).all()

    if len(suspicious_transactions) >= min_transactions:
        total_amount = sum(tx.amount for tx in suspicious_transactions)
        return (f"Structuring (Payments) Detected: User sent {len(suspicious_transactions)} payments totaling "
                f"₹{total_amount:,.2f} in the last {time_window_hours} hours.")
    return None

# --- RULE 2: Detects a user RECEIVING multiple small deposits ---
def check_structuring_by_deposit(db: Session, user: User, amount_threshold: float = 50000.0, time_window_hours: int = 48, min_transactions: int = 4) -> str | None:
    """
    Flags a user for RECEIVING multiple deposits just under the threshold.
    This can be a signal that the user is a "mule" account.
    """
    window_start_time = datetime.now() - timedelta(hours=time_window_hours)
    
    suspicious_transactions = db.query(Transaction).filter(
        and_(
            Transaction.to_user_id == user.id, # The user is the RECEIVER
            Transaction.timestamp >= window_start_time,
            Transaction.amount < amount_threshold,
            Transaction.amount > amount_threshold * 0.8
        )
    ).all()

    if len(suspicious_transactions) >= min_transactions:
        total_amount = sum(tx.amount for tx in suspicious_transactions)
        return (f"Structuring (Deposits) Detected: User received {len(suspicious_transactions)} deposits totaling "
                f"₹{total_amount:,.2f} in the last {time_window_hours} hours.")
    return None