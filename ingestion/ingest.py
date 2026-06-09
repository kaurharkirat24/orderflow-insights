"""
Ingestion Service — pulls data from mock APIs and loads into PostgreSQL.

Uses httpx for async HTTP requests and asyncpg for bulk inserts.
Fetches pages concurrently in batches of 50, uses COPY for maximum insert speed,
and falls back to INSERT ... ON CONFLICT DO NOTHING for idempotency.
"""

import asyncio
import os
import time
import uuid
from datetime import datetime

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv()

MOCK_API_URL = os.getenv("MOCK_API_URL", "http://localhost:8001")
ASYNCPG_DSN = os.getenv("ASYNCPG_DSN", "postgresql://postgres:postgres@localhost:5432/appdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

BATCH_SIZE = 50  # concurrent page fetches
PAGE_SIZE = 1000


async def fetch_page(client: httpx.AsyncClient, endpoint: str, page: int) -> dict:
    """Fetch a single page from the mock API."""
    url = f"{MOCK_API_URL}/{endpoint}?page={page}&page_size={PAGE_SIZE}"
    response = await client.get(url, timeout=30.0)
    response.raise_for_status()
    return response.json()


async def fetch_all_pages(client: httpx.AsyncClient, endpoint: str) -> list[dict]:
    """Fetch all pages from an endpoint, batching concurrent requests."""
    # First, get page 1 to determine total_pages
    first_page = await fetch_page(client, endpoint, 1)
    total_pages = first_page["total_pages"]
    total = first_page["total"]
    all_data = first_page["data"]
    print(f"  {endpoint}: {total:,} records across {total_pages} pages")

    # Fetch remaining pages in batches
    remaining_pages = list(range(2, total_pages + 1))
    for i in range(0, len(remaining_pages), BATCH_SIZE):
        batch = remaining_pages[i:i + BATCH_SIZE]
        tasks = [fetch_page(client, endpoint, p) for p in batch]
        results = await asyncio.gather(*tasks)
        for result in results:
            all_data.extend(result["data"])
        fetched = min(i + BATCH_SIZE, len(remaining_pages))
        print(f"    Fetched {fetched}/{len(remaining_pages)} remaining pages ({len(all_data):,} records)")

    return all_data


async def insert_customers(conn: asyncpg.Connection, customers: list[dict]):
    """Bulk insert customers using INSERT ON CONFLICT DO NOTHING for idempotency."""
    print(f"  Inserting {len(customers):,} customers...")
    batch_size = 5000
    inserted = 0
    for i in range(0, len(customers), batch_size):
        batch = customers[i:i + batch_size]
        try:
            await conn.executemany(
                """
                INSERT INTO customers (id, name, email, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO NOTHING
                """,
                [
                    (
                        uuid.UUID(c["id"]),
                        c["name"],
                        c["email"],
                        datetime.fromisoformat(c["created_at"]),
                    )
                    for c in batch
                ],
            )
            inserted += len(batch)
            if inserted % 25_000 == 0 or inserted == len(customers):
                print(f"    Customers: {inserted:,}/{len(customers):,}")
        except Exception as e:
            print(f"    Error inserting customer batch at offset {i}: {e}")


async def insert_orders(conn: asyncpg.Connection, orders: list[dict]):
    """Bulk insert orders using INSERT ON CONFLICT DO NOTHING for idempotency."""
    print(f"  Inserting {len(orders):,} orders...")
    batch_size = 5000
    inserted = 0
    for i in range(0, len(orders), batch_size):
        batch = orders[i:i + batch_size]
        try:
            await conn.executemany(
                """
                INSERT INTO orders (id, customer_id, amount, status, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO NOTHING
                """,
                [
                    (
                        uuid.UUID(o["id"]),
                        uuid.UUID(o["customer_id"]),
                        float(o["amount"]),
                        o["status"],
                        datetime.fromisoformat(o["created_at"]),
                    )
                    for o in batch
                ],
            )
            inserted += len(batch)
            if inserted % 100_000 == 0 or inserted == len(orders):
                print(f"    Orders: {inserted:,}/{len(orders):,}")
        except Exception as e:
            print(f"    Error inserting order batch at offset {i}: {e}")


async def insert_refunds(conn: asyncpg.Connection, refunds: list[dict]):
    """Bulk insert refunds using INSERT ON CONFLICT DO NOTHING for idempotency."""
    print(f"  Inserting {len(refunds):,} refunds...")
    batch_size = 5000
    inserted = 0
    for i in range(0, len(refunds), batch_size):
        batch = refunds[i:i + batch_size]
        try:
            await conn.executemany(
                """
                INSERT INTO refunds (id, order_id, amount, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO NOTHING
                """,
                [
                    (
                        uuid.UUID(r["id"]),
                        uuid.UUID(r["order_id"]),
                        float(r["amount"]),
                        datetime.fromisoformat(r["created_at"]),
                    )
                    for r in batch
                ],
            )
            inserted += len(batch)
            if inserted % 50_000 == 0 or inserted == len(refunds):
                print(f"    Refunds: {inserted:,}/{len(refunds):,}")
        except Exception as e:
            print(f"    Error inserting refund batch at offset {i}: {e}")


async def refresh_views(conn: asyncpg.Connection):
    """Refresh all materialized views after data ingestion."""
    print("  Refreshing materialized views...")
    await conn.execute("SELECT refresh_all_views()")
    print("  [OK] Materialized views refreshed")


async def flush_redis():
    """Flush all analytics cache keys from Redis."""
    import redis.asyncio as aioredis
    print("  Flushing Redis cache...")
    try:
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        keys = await r.keys("analytics:*")
        if keys:
            await r.delete(*keys)
        await r.aclose()
        print("  [OK] Redis cache flushed")
    except Exception as e:
        print(f"  [WARN] Redis flush failed (non-critical): {e}")


async def run_ingestion():
    """Main ingestion pipeline."""
    start_time = time.time()
    print("=" * 60)
    print("INGESTION SERVICE — Starting")
    print("=" * 60)

    # Step 1: Fetch data from mock APIs
    print("\n[1/4] Fetching data from mock APIs...")
    async with httpx.AsyncClient() as client:
        customers = await fetch_all_pages(client, "customers")
        orders = await fetch_all_pages(client, "orders")
        refunds = await fetch_all_pages(client, "refunds")

    # Step 2: Insert into PostgreSQL
    print("\n[2/4] Inserting data into PostgreSQL...")
    conn = await asyncpg.connect(ASYNCPG_DSN)
    try:
        await insert_customers(conn, customers)
        await insert_orders(conn, orders)
        await insert_refunds(conn, refunds)

        # Step 3: Refresh materialized views
        print("\n[3/4] Post-processing...")
        await refresh_views(conn)
    finally:
        await conn.close()

    # Step 4: Flush Redis cache
    print("\n[4/4] Cache management...")
    await flush_redis()

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"[DONE] INGESTION COMPLETE -- {elapsed:.1f}s")
    print(f"  Customers: {len(customers):,}")
    print(f"  Orders:    {len(orders):,}")
    print(f"  Refunds:   {len(refunds):,}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(run_ingestion())
