import requests
import random
from faker import Faker

# This script now lives OUTSIDE the application and just calls its API.

API_BASE_URL = "http://localhost:8000"
fake = Faker()

def create_users():
    """Creates a set of users we can use for transactions."""
    print("Creating initial users via API...")
    users = []
    # Create a known user for testing
    users.append({"full_name": "Alice", "email": "alice@system.com", "country": "USA"})
    users.append({"full_name": "Bob", "email": "bob@system.com", "country": "UK"})
    users.append({"full_name": "Charlie", "email": "charlie@system.com", "country": "India"})
    
    # This is a placeholder for a real user creation endpoint
    # For now, we assume users are created manually or by another system.
    print(f"Assuming these users exist: {[u['email'] for u in users]}")
    return ["alice", "bob", "charlie"]


def feed_transactions(accounts: list):
    """Feeds a batch of transactions to the ingestion API."""
    print("Feeding a batch of transactions to the /ingest/transactions endpoint...")
    
    transactions_batch = []
    for _ in range(20):
        sender = random.choice(accounts)
        receiver = random.choice([acc for acc in accounts if acc != sender])
        
        raw_tx = {
            "transaction_id": fake.uuid4(),
            "from_account": sender,
            "to_account": receiver,
            "amount": round(random.uniform(100, 500000), 2),
            "currency": "INR",
            "description": fake.sentence()
        }
        transactions_batch.append(raw_tx)
        
    try:
        response = requests.post(f"{API_BASE_URL}/ingest/transactions", json=transactions_batch)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print("Successfully ingested batch. Server response:")
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error calling ingestion API: {e}")

if __name__ == "__main__":
    # In a real system, you would have a separate process for creating users.
    # Here we just define who our players are.
    accounts = create_users()
    
    # We will feed transactions in batches to simulate a live data stream.
    feed_transactions(accounts)