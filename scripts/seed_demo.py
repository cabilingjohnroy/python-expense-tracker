"""Fill a SEPARATE demo database with realistic sample transactions.

Used by demo.bat for screenshots and trying the app. It refuses to run unless
FLOWMONEY_DATA_DIR is set, so it can never touch your real data in AppData.
"""
import os
import random
import sys
from datetime import date

if not os.environ.get("FLOWMONEY_DATA_DIR"):
    sys.exit("Refusing to seed: set FLOWMONEY_DATA_DIR to a demo folder first (see demo.bat).")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402
from reports import shift_month  # noqa: E402

random.seed(7)  # same demo data every time
database.create_database()
with database._connect() as connection:
    connection.execute("DELETE FROM transactions")

today = date.today()
this_month = today.replace(day=1)

EXPENSES = [
    ("Food", 120, 380, 9),
    ("Transport", 25, 90, 7),
    ("School", 150, 900, 2),
    ("Load", 50, 100, 2),
    ("Entertainment", 150, 450, 2),
]

for offset in range(-5, 1):
    month = shift_month(this_month, offset)
    last_day = today.day if month == this_month else 28

    def day(n):
        return month.replace(day=min(n, last_day)).isoformat()

    database.add_transaction("Income", "Allowance", 6000, day(1))
    if offset % 2 == 0:
        database.add_transaction("Income", "Freelance", random.choice([1500, 2500, 3200]), day(15))
    database.add_transaction("Expense", "Bills", random.choice([850, 920, 1100]), day(5))
    for category, low, high, times in EXPENSES:
        for _ in range(times):
            amount = round(random.uniform(low, high), 2)
            database.add_transaction("Expense", category, amount, day(random.randint(1, 28)))

print(f"Demo data ready: {len(database.get_transactions())} transactions in {database.DATABASE}")
