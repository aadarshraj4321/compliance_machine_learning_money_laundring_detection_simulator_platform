import csv
import io
from sqlalchemy.orm import Session
from app.models import User, Transaction

def map_and_process_csv(db: Session, file_content: bytes) -> int:
    """
    Reads a CSV, creates users, and saves transactions to the database.
    It NO LONGER triggers celery tasks. It only processes data.
    """
    processed_count = 0
    file_stream = io.StringIO(file_content.decode('utf-8'))
    reader = csv.DictReader(file_stream)
    
    rows = list(reader)
    all_accounts = set()
    for row in rows:
        if row.get('Debit_Account'): all_accounts.add(row['Debit_Account'])
        if row.get('Credit_Account'): all_accounts.add(row['Credit_Account'])
    
    user_map = {}
    for acc in all_accounts:
        user = db.query(User).filter(User.email == f"{acc}@bank.com").first()
        if not user:
            user = User(full_name=acc, email=f"{acc}@bank.com", country="Unknown")
            db.add(user)
            db.commit()
            db.refresh(user)
        user_map[acc] = user.id

    for row in rows:
        from_user_id = user_map.get(row.get('Debit_Account'))
        to_user_id = user_map.get(row.get('Credit_Account'))
        
        # We only process P2P transactions for this logic
        if not from_user_id or not to_user_id:
            continue

        db_transaction = Transaction(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=float(row['Amount']),
            currency=row['Currency'],
            description=row['Description']
        )
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)

        # THE TRIGGER LOGIC IS REMOVED FROM HERE
        processed_count += 1
        
    return processed_count