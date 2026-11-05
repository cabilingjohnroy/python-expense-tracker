
import sqlite3
import os
from pathlib import Path

# Store the database in Windows AppData
app_data = Path(os.environ.get("APPDATA", Path.home())) / "FlowMoney"
app_data.mkdir(parents=True, exist_ok=True)

DATABASE = str(app_data / "expenses.db")


def create_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def add_transaction(type, category, amount, date):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO transactions (type, category, amount, date)
        VALUES (?, ?, ?, ?)
    """, (type, category, amount, date))

    connection.commit()
    connection.close()


def get_transactions():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM transactions
        ORDER BY id DESC
    """)

    transactions = cursor.fetchall()
    connection.close()

    return transactions


def delete_transaction(transaction_id):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM transactions WHERE id = ?",
        (transaction_id,)
    )

    connection.commit()
    connection.close()


def get_totals():
    transactions = get_transactions()

    income = 0
    expenses = 0

    for transaction in transactions:
        transaction_type = transaction[1]
        amount = transaction[3]

        if transaction_type == "Income":
            income += amount
        else:
            expenses += amount

    balance = income - expenses

    return income, expenses, balance
