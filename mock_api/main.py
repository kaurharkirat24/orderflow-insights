"""
Mock API — serves generated data with paginated endpoints.

Runs on port 8001. Loads all JSON data into memory at startup.
"""

import json
import math
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query

from mock_api.routers import customers, orders, refunds

# Global data store
data_store = {
    "customers": [],
    "orders": [],
    "refunds": [],
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load JSON data files into memory at startup."""
    print("Loading data files into memory...")
    for dataset in ["customers", "orders", "refunds"]:
        filepath = os.path.join(DATA_DIR, f"{dataset}.json")
        with open(filepath, "r") as f:
            data_store[dataset] = json.load(f)
        print(f"  Loaded {len(data_store[dataset]):,} {dataset}")
    print("Mock API ready!")
    yield
    print("Mock API shutting down...")


app = FastAPI(title="Mock Data API", version="1.0.0", lifespan=lifespan)

app.include_router(customers.router)
app.include_router(orders.router)
app.include_router(refunds.router)


def paginate(data: list, page: int, page_size: int) -> dict:
    """Generic pagination helper."""
    total = len(data)
    total_pages = math.ceil(total / page_size)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "data": data[start:end],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
    }
