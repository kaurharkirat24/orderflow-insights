"""
Data Generator — generates reproducible seed data for the analytics backend.

Uses Faker with seed 42 to generate:
- 100,000 customers
- 1,000,000 orders (70% completed, 20% pending, 10% cancelled)
- 200,000 refunds (each referencing a completed order)
"""

import json
import os
import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

# Reproducible seeds
fake = Faker()
Faker.seed(42)
random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FIXED_NOW = datetime(2026, 1, 1, 0, 0, 0)
UUID_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(prefix: str, index: int) -> str:
    """Create stable UUIDs so repeated generation produces identical data."""
    return str(uuid.uuid5(UUID_NAMESPACE, f"{prefix}-{index}"))


def generate_customers(count: int = 100_000) -> list[dict]:
    """Generate customer records with unique emails."""
    print(f"Generating {count:,} customers...")
    now = FIXED_NOW
    three_years_ago = now - timedelta(days=3 * 365)
    total_seconds = int((now - three_years_ago).total_seconds())

    customers = []
    emails_seen = set()
    for i in range(count):
        # Ensure unique emails
        while True:
            email = fake.email()
            if email not in emails_seen:
                emails_seen.add(email)
                break

        created_at = three_years_ago + timedelta(seconds=random.randint(0, total_seconds))
        customers.append({
            "id": deterministic_uuid("customer", i),
            "name": fake.name(),
            "email": email,
            "created_at": created_at.isoformat(),
        })
        if (i + 1) % 25_000 == 0:
            print(f"  Customers: {i + 1:,}/{count:,}")

    print(f"  [OK] Generated {len(customers):,} customers")
    return customers


def generate_orders(customers: list[dict], count: int = 1_000_000) -> list[dict]:
    """Generate order records linked to customers."""
    print(f"Generating {count:,} orders...")
    customer_ids = [c["id"] for c in customers]
    now = FIXED_NOW
    two_years_ago = now - timedelta(days=2 * 365)
    total_seconds = int((now - two_years_ago).total_seconds())

    statuses = ["completed", "pending", "cancelled"]
    weights = [70, 20, 10]

    orders = []
    for i in range(count):
        customer_id = random.choice(customer_ids)
        status = random.choices(statuses, weights=weights, k=1)[0]
        amount = round(random.uniform(5.00, 2000.00), 2)
        created_at = two_years_ago + timedelta(seconds=random.randint(0, total_seconds))

        orders.append({
            "id": deterministic_uuid("order", i),
            "customer_id": customer_id,
            "amount": amount,
            "status": status,
            "created_at": created_at.isoformat(),
        })
        if (i + 1) % 250_000 == 0:
            print(f"  Orders: {i + 1:,}/{count:,}")

    print(f"  [OK] Generated {len(orders):,} orders")
    return orders


def generate_refunds(orders: list[dict], count: int = 200_000) -> list[dict]:
    """Generate refund records linked to completed orders."""
    print(f"Generating {count:,} refunds...")
    completed_orders = [o for o in orders if o["status"] == "completed"]
    print(f"  Found {len(completed_orders):,} completed orders for refund selection")

    # Sample completed orders for refunds (with replacement since count may exceed unique completed orders)
    selected_orders = random.choices(completed_orders, k=count)

    refunds = []
    for i, order in enumerate(selected_orders):
        # Refund amount is 50-100% of order amount
        refund_pct = random.uniform(0.50, 1.00)
        refund_amount = round(order["amount"] * refund_pct, 2)

        # Refund created_at is after order's created_at
        order_dt = datetime.fromisoformat(order["created_at"])
        max_days_after = (FIXED_NOW - order_dt).days
        if max_days_after <= 0:
            max_days_after = 1
        days_after = random.randint(1, min(max_days_after, 90))
        refund_dt = order_dt + timedelta(days=days_after)

        refunds.append({
            "id": deterministic_uuid("refund", i),
            "order_id": order["id"],
            "amount": refund_amount,
            "created_at": refund_dt.isoformat(),
        })
        if (i + 1) % 50_000 == 0:
            print(f"  Refunds: {i + 1:,}/{count:,}")

    print(f"  [OK] Generated {len(refunds):,} refunds")
    return refunds


def write_json(data: list[dict], filename: str):
    """Write data to a JSON file in the data directory."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f)
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  Written {filepath} ({size_mb:.1f} MB)")


def main():
    print("=" * 60)
    print("DATA GENERATOR — Seed 42")
    print("=" * 60)

    # Reset seeds to ensure reproducibility on re-runs
    Faker.seed(42)
    random.seed(42)

    customers = generate_customers()
    orders = generate_orders(customers)
    refunds = generate_refunds(orders)

    print("\nWriting JSON files...")
    write_json(customers, "customers.json")
    write_json(orders, "orders.json")
    write_json(refunds, "refunds.json")

    print("\n[DONE] Data generation complete!")
    print(f"  Customers: {len(customers):,}")
    print(f"  Orders:    {len(orders):,}")
    print(f"  Refunds:   {len(refunds):,}")


if __name__ == "__main__":
    main()
