import sqlite3
import os
from contextlib import closing, contextmanager
from pathlib import Path

# Store the database in Windows AppData
app_data = Path(os.environ.get("APPDATA", Path.home())) / "FlowMoney"
app_data.mkdir(parents=True, exist_ok=True)

DATABASE = str(app_data / "expenses.db")


@contextmanager
def _connect():
    """Open a connection, commit on success, roll back on error, always close."""
    with closing(sqlite3.connect(DATABASE)) as connection:
        with connection:  # commits, or rolls back if an exception is raised
            yield connection


def create_database():
    with _connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL
            )
        """)
        # Speeds up date sorting and monthly reports as the table grows.
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (date)"
        )


def add_transaction(t_type, category, amount, date):
    if t_type not in ("Income", "Expense"):
        raise ValueError(f"Unknown transaction type: {t_type!r}")
    with _connect() as connection:
        connection.execute(
            "INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)",
            (t_type, category, amount, date),
        )


def get_transactions(limit=None):
    """Newest first (by transaction date, then by entry order)."""
    query = "SELECT id, type, category, amount, date FROM transactions ORDER BY date DESC, id DESC"
    params = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (int(limit),)
    with _connect() as connection:
        return connection.execute(query, params).fetchall()


def get_categories():
    """Distinct categories the user has already used, most used first."""
    with _connect() as connection:
        rows = connection.execute("""
            SELECT category FROM transactions
            GROUP BY category
            ORDER BY COUNT(*) DESC, category
        """).fetchall()
    return [row[0] for row in rows]


def delete_transaction(transaction_id):
    with _connect() as connection:
        connection.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))


def get_totals():
    """Return (income, expenses, balance), computed by SQLite instead of in Python."""
    with _connect() as connection:
        income, expenses = connection.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN type = 'Income' THEN amount END), 0),
                COALESCE(SUM(CASE WHEN type = 'Expense' THEN amount END), 0)
            FROM transactions
        """).fetchone()
    return income, expenses, income - expenses
