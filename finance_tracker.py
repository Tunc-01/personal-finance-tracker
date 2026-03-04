from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

DATE_FMT = "%Y-%m-%d"
DATA_FILE = "transactions.csv"


@dataclass
class Transaction:
    """
    Represents a single financial transaction.
    amount: positive for income, negative for expense
    """
    tx_date: date
    amount: float
    category: str
    note: str

    @property
    def is_income(self) -> bool:
        return self.amount >= 0

    @property
    def is_expense(self) -> bool:
        return self.amount < 0


def parse_date(s: str) -> date:
    return datetime.strptime(s.strip(), DATE_FMT).date()


def format_money(x: float) -> str:
    sign = "-" if x < 0 else ""
    x_abs = abs(x)
    return f"{sign}{x_abs:,.2f}"


def ensure_csv_exists(filename: str) -> None:
    if not os.path.exists(filename):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "amount", "category", "note"])


def load_transactions(filename: str) -> List[Transaction]:
    ensure_csv_exists(filename)
    transactions: List[Transaction] = []
    with open(filename, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                tx = Transaction(
                    tx_date=parse_date(row["date"]),
                    amount=float(row["amount"]),
                    category=row["category"].strip() or "Uncategorized",
                    note=row.get("note", "").strip(),
                )
                transactions.append(tx)
            except Exception:
                # Skip corrupted rows rather than crashing
                continue
    # newest first
    transactions.sort(key=lambda t: t.tx_date, reverse=True)
    return transactions


def save_transaction(filename: str, tx: Transaction) -> None:
    ensure_csv_exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([tx.tx_date.strftime(DATE_FMT), tx.amount, tx.category, tx.note])


def input_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            print("Please enter a valid number (e.g., 1200.50).")


def input_date(prompt: str) -> date:
    while True:
        raw = input(prompt).strip()
        try:
            return parse_date(raw)
        except ValueError:
            print(f"Please enter a valid date in format {DATE_FMT} (e.g., 2026-03-04).")


def input_nonempty(prompt: str, default: Optional[str] = None) -> str:
    while True:
        raw = input(prompt).strip()
        if raw:
            return raw
        if default is not None:
            return default
        print("This field cannot be empty.")


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def summarize(transactions: List[Transaction]) -> Dict[str, float]:
    income = sum(t.amount for t in transactions if t.is_income)
    expense = sum(t.amount for t in transactions if t.is_expense)
    balance = income + expense
    return {"income": income, "expense": expense, "balance": balance}


def category_breakdown(transactions: List[Transaction]) -> Dict[str, float]:
    by_cat: Dict[str, float] = {}
    for t in transactions:
        by_cat.setdefault(t.category, 0.0)
        by_cat[t.category] += t.amount
    # sort by absolute impact
    return dict(sorted(by_cat.items(), key=lambda kv: abs(kv[1]), reverse=True))


def monthly_breakdown(transactions: List[Transaction]) -> Dict[str, Dict[str, float]]:
    by_month: Dict[str, List[Transaction]] = {}
    for t in transactions:
        by_month.setdefault(month_key(t.tx_date), []).append(t)

    result: Dict[str, Dict[str, float]] = {}
    for m, txs in by_month.items():
        result[m] = summarize(txs)
    # sort by month descending
    return dict(sorted(result.items(), key=lambda kv: kv[0], reverse=True))


def filter_by_month(transactions: List[Transaction], yyyy_mm: str) -> List[Transaction]:
    yyyy_mm = yyyy_mm.strip()
    return [t for t in transactions if month_key(t.tx_date) == yyyy_mm]


def filter_by_date_range(transactions: List[Transaction], start: date, end: date) -> List[Transaction]:
    # inclusive range
    return [t for t in transactions if start <= t.tx_date <= end]


def print_transactions(transactions: List[Transaction], limit: int = 25) -> None:
    if not transactions:
        print("No transactions found.")
        return

    print("-" * 80)
    print(f"{'Date':10}  {'Amount':>12}  {'Category':20}  Note")
    print("-" * 80)
    for t in transactions[:limit]:
        amt = format_money(t.amount)
        print(f"{t.tx_date.strftime(DATE_FMT):10}  {amt:>12}  {t.category[:20]:20}  {t.note}")
    if len(transactions) > limit:
        print(f"... and {len(transactions) - limit} more")
    print("-" * 80)


def print_summary(title: str, s: Dict[str, float]) -> None:
    print(f"\n{title}")
    print(f"  Income : {format_money(s['income'])}")
    print(f"  Expense: {format_money(s['expense'])}")
    print(f"  Balance: {format_money(s['balance'])}")


def add_transaction_flow(filename: str) -> None:
    print("\nAdd Transaction")
    tx_date = input_date(f"Date ({DATE_FMT}): ")
    kind = input_nonempty("Type (income/expense): ").lower()
    amount = input_float("Amount: ")
    category = input_nonempty("Category (e.g., Food, Rent, Salary): ", default="Uncategorized")
    note = input("Note (optional): ").strip()

    if kind.startswith("e"):
        amount = -abs(amount)
    else:
        amount = abs(amount)

    tx = Transaction(tx_date=tx_date, amount=amount, category=category, note=note)
    save_transaction(filename, tx)
    print("✅ Saved.")


def report_overall(transactions: List[Transaction]) -> None:
    s = summarize(transactions)
    print_summary("Overall Summary", s)

    by_cat = category_breakdown(transactions)
    print("\nTop Categories (net amount; income positive, expense negative):")
    for cat, amt in list(by_cat.items())[:10]:
        print(f"  {cat:20} {format_money(amt)}")


def report_monthly(transactions: List[Transaction]) -> None:
    mb = monthly_breakdown(transactions)
    if not mb:
        print("No data.")
        return

    print("\nMonthly Summary")
    print("-" * 60)
    print(f"{'Month':7}  {'Income':>12}  {'Expense':>12}  {'Balance':>12}")
    print("-" * 60)
    for m, s in mb.items():
        print(
            f"{m:7}  {format_money(s['income']):>12}  {format_money(s['expense']):>12}  {format_money(s['balance']):>12}"
        )
    print("-" * 60)

    # Drill down into a specific month
    choice = input("\nEnter a month to view details (YYYY-MM) or press Enter to skip: ").strip()
    if choice:
        txs = filter_by_month(transactions, choice)
        print_transactions(txs, limit=50)
        print_summary(f"Summary for {choice}", summarize(txs))


def report_date_range(transactions: List[Transaction]) -> None:
    print("\nDate Range Report")
    start = input_date(f"Start date ({DATE_FMT}): ")
    end = input_date(f"End date ({DATE_FMT}): ")
    txs = filter_by_date_range(transactions, start, end)
    print_transactions(txs, limit=50)
    print_summary(f"Summary {start.strftime(DATE_FMT)} → {end.strftime(DATE_FMT)}", summarize(txs))


def quick_demo_data(filename: str) -> None:
    """
    Adds a few sample transactions so the project looks alive.
    """
    samples = [
        Transaction(parse_date("2026-03-01"), 35000, "Salary", "Monthly salary"),
        Transaction(parse_date("2026-03-02"), -250, "Food", "Groceries"),
        Transaction(parse_date("2026-03-02"), -120, "Transport", "Metro card"),
        Transaction(parse_date("2026-03-03"), -4500, "Rent", "Monthly rent"),
        Transaction(parse_date("2026-03-03"), -300, "Subscriptions", "Streaming services"),
        Transaction(parse_date("2026-03-04"), -800, "Education", "Online course"),
    ]
    for tx in samples:
        save_transaction(filename, tx)
    print("✅ Demo data added.")


def menu() -> None:
    print("\nPersonal Finance Tracker")
    print("1) Add transaction")
    print("2) View last transactions")
    print("3) Overall report")
    print("4) Monthly report")
    print("5) Date range report")
    print("6) Add demo data")
    print("7) Exit")


def main() -> None:
    filename = DATA_FILE
    ensure_csv_exists(filename)

    while True:
        transactions = load_transactions(filename)
        menu()
        choice = input("Choose: ").strip()

        if choice == "1":
            add_transaction_flow(filename)
        elif choice == "2":
            print_transactions(transactions, limit=30)
        elif choice == "3":
            report_overall(transactions)
        elif choice == "4":
            report_monthly(transactions)
        elif choice == "5":
            report_date_range(transactions)
        elif choice == "6":
            quick_demo_data(filename)
        elif choice == "7":
            print("Bye!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
