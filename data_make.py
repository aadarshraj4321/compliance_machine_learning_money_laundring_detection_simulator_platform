import csv
import random
from faker import Faker
from datetime import datetime, timedelta

# --- Configuration ---
NUM_USERS = 500
NUM_TRANSACTIONS = 10000
OUTPUT_FILE = 'large_bank_data.csv'

# --- Initialize Faker ---
fake = Faker()

def generate_big_data():
    print(f"Generating a large dataset with {NUM_USERS} users and {NUM_TRANSACTIONS} transactions...")

    # --- Create a pool of user accounts ---
    accounts = [f"ACC{1000 + i}" for i in range(NUM_USERS)]
    
    # --- Define our "Criminal Syndicates" ---
    
    # Syndicate 1: Structuring & Layering (led by a "Kingpin")
    kingpin_acc = "ACC1000"
    lieutenant_accs = ["ACC1001", "ACC1002"]
    mule_accs_1 = [f"ACC{1003 + i}" for i in range(10)]
    
    # Syndicate 2: A simple circular loop
    loop_accs = ["ACC1300", "ACC1301", "ACC1302", "ACC1303"]

    # --- Open the CSV file for writing ---
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write the header row (like a real bank export)
        writer.writerow(['Date', 'Transaction_ID', 'Debit_Account', 'Credit_Account', 'Amount', 'Currency', 'Description'])
        
        # --- Generate Embedded Suspicious Patterns ---
        
        # 1. Kingpin funds the lieutenants (large, anomalous transactions)
        print("  - Generating Kingpin funding transactions...")
        for i, acc in enumerate(lieutenant_accs):
            writer.writerow([
                (datetime.now() - timedelta(days=20)).isoformat(),
                f"KP_FUND_{i}",
                kingpin_acc,
                acc,
                random.uniform(5000000, 10000000), # Large amounts
                "INR",
                "Investment Capital"
            ])
        
        # 2. Lieutenants perform structuring into mule accounts
        print("  - Generating Structuring transactions...")
        for _ in range(50): # 50 small deposits
            writer.writerow([
                (datetime.now() - timedelta(days=random.randint(5, 15))).isoformat(),
                fake.uuid4(),
                random.choice(lieutenant_accs),
                random.choice(mule_accs_1),
                random.uniform(40000, 49999), # Classic structuring amounts
                "INR",
                "Cash Deposit"
            ])
            
        # 3. Mules layer the money among themselves
        print("  - Generating Layering transactions...")
        for _ in range(100):
            sender = random.choice(mule_accs_1)
            receiver = random.choice([m for m in mule_accs_1 if m != sender])
            writer.writerow([
                (datetime.now() - timedelta(days=random.randint(2, 10))).isoformat(),
                fake.uuid4(),
                sender,
                receiver,
                random.uniform(10000, 35000),
                "INR",
                "Service Payment"
            ])

        # 4. The second syndicate's circular loop
        print("  - Generating Circular Loop transactions...")
        for i in range(len(loop_accs)):
            sender = loop_accs[i]
            receiver = loop_accs[(i + 1) % len(loop_accs)] # a->b, b->c, c->d, d->a
            writer.writerow([
                (datetime.now() - timedelta(days=1)).isoformat(),
                f"LOOP_TXN_{i}",
                sender,
                receiver,
                150000,
                "INR",
                "Consulting Fee"
            ])

        # --- Generate "Noise" - Normal Transactions ---
        print(f"  - Generating {NUM_TRANSACTIONS - 200} normal 'noise' transactions...")
        # We subtract the ~200 suspicious transactions we've already made
        for _ in range(NUM_TRANSACTIONS - 200):
            sender = random.choice(accounts)
            receiver = random.choice([acc for acc in accounts if acc != sender])
            writer.writerow([
                (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                fake.uuid4(),
                sender,
                receiver,
                random.uniform(100, 80000), # Normal transaction amounts
                "INR",
                random.choice(["Online Shopping", "Bill Payment", "Friend Transfer", "Restaurant"])
            ])
            
    print(f"\nDone! Big data file '{OUTPUT_FILE}' created successfully.")

if __name__ == '__main__':
    generate_big_data()