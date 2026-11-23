"""Pure report/date helpers, kept separate from the GUI so they can be unit-tested."""
from datetime import date

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Bills", "Shopping", "School",
    "Health", "Entertainment", "Allowance", "Salary", "Other",
]


def shift_month(month_start, months):
    """Return the first day of the month `months` away from `month_start`."""
    index = month_start.year * 12 + (month_start.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def month_key(month_start):
    """date(2026, 11, 1) -> '2026-11' (the prefix used by stored dates)."""
    return month_start.strftime("%Y-%m")


def month_label(month_start):
    """date(2026, 11, 1) -> 'November 2026'."""
    return month_start.strftime("%B %Y")


def records_in_month(records, month_start):
    """Records are (id, type, category, amount, 'YYYY-MM-DD') tuples."""
    prefix = month_key(month_start) + "-"
    return [r for r in records if str(r[4]).startswith(prefix)]


def monthly_totals(records, end_month, count=6):
    """Income/expense totals for the `count` months ending at `end_month`, oldest first.

    Returns a list of (month_start, income, expense).
    """
    months = [shift_month(end_month, offset) for offset in range(-(count - 1), 1)]
    totals = {month_key(m): [0.0, 0.0] for m in months}
    for _, kind, _, amount, when in records:
        bucket = totals.get(str(when)[:7])
        if bucket is not None:
            bucket[0 if kind == "Income" else 1] += float(amount)
    return [(m, *totals[month_key(m)]) for m in months]


def normalize_category(typed, existing):
    """Clean up a typed category and reuse an existing spelling when one matches.

    "  food " with existing ["Food"] -> "Food", so "Food" and "food" don't
    become two separate categories in the report.
    """
    cleaned = " ".join(typed.split())
    for name in existing:
        if name.lower() == cleaned.lower():
            return name
    return cleaned[:1].upper() + cleaned[1:]


def category_choices(existing):
    """Defaults first, then any of the user's own categories, without duplicates."""
    seen = set()
    choices = []
    for name in list(DEFAULT_CATEGORIES) + list(existing):
        if name.lower() not in seen:
            seen.add(name.lower())
            choices.append(name)
    return choices
