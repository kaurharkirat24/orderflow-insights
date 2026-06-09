"""
Analytics API endpoints — all 8 analytics queries with Redis caching.

Each endpoint reads from materialized views and caches results for 60 seconds.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_get, cache_set
from app.database import get_db
from app.schemas import (
    TotalOrdersResponse,
    TotalRevenueResponse,
    TotalRefundsResponse,
    NetRevenueResponse,
    AvgOrderValueResponse,
    RepeatCustomerRevenueResponse,
    RevenueTrendsResponse,
    RevenueTrendItem,
    TopCustomerItem,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/total-orders", response_model=TotalOrdersResponse)
async def get_total_orders(db: AsyncSession = Depends(get_db)):
    """Total number of orders across all statuses."""
    cached = await cache_get("analytics:total-orders")
    if cached:
        return cached

    result = await db.execute(text("SELECT total_orders FROM mv_analytics_summary"))
    row = result.fetchone()
    data = {"total_orders": int(row[0]) if row else 0}
    await cache_set("analytics:total-orders", data)
    return data


@router.get("/total-revenue", response_model=TotalRevenueResponse)
async def get_total_revenue(db: AsyncSession = Depends(get_db)):
    """Total revenue from completed orders only."""
    cached = await cache_get("analytics:total-revenue")
    if cached:
        return cached

    result = await db.execute(text("SELECT total_revenue FROM mv_analytics_summary"))
    row = result.fetchone()
    data = {"total_revenue": float(row[0]) if row else 0.0}
    await cache_set("analytics:total-revenue", data)
    return data


@router.get("/total-refunds", response_model=TotalRefundsResponse)
async def get_total_refunds(db: AsyncSession = Depends(get_db)):
    """Total refund count and total refund amount."""
    cached = await cache_get("analytics:total-refunds")
    if cached:
        return cached

    result = await db.execute(
        text("SELECT total_refunds, total_refund_amount FROM mv_analytics_summary")
    )
    row = result.fetchone()
    data = {
        "total_refunds": int(row[0]) if row else 0,
        "total_refund_amount": float(row[1]) if row else 0.0,
    }
    await cache_set("analytics:total-refunds", data)
    return data


@router.get("/net-revenue", response_model=NetRevenueResponse)
async def get_net_revenue(db: AsyncSession = Depends(get_db)):
    """Net revenue = total_revenue - total_refund_amount."""
    cached = await cache_get("analytics:net-revenue")
    if cached:
        return cached

    result = await db.execute(text("SELECT net_revenue FROM mv_analytics_summary"))
    row = result.fetchone()
    data = {"net_revenue": float(row[0]) if row else 0.0}
    await cache_set("analytics:net-revenue", data)
    return data


@router.get("/avg-order-value", response_model=AvgOrderValueResponse)
async def get_avg_order_value(db: AsyncSession = Depends(get_db)):
    """Average order value of completed orders."""
    cached = await cache_get("analytics:avg-order-value")
    if cached:
        return cached

    result = await db.execute(text("SELECT avg_order_value FROM mv_analytics_summary"))
    row = result.fetchone()
    data = {"avg_order_value": round(float(row[0]), 2) if row else 0.0}
    await cache_set("analytics:avg-order-value", data)
    return data


@router.get("/repeat-customer-revenue", response_model=RepeatCustomerRevenueResponse)
async def get_repeat_customer_revenue(db: AsyncSession = Depends(get_db)):
    """Revenue from customers with more than one completed order."""
    cached = await cache_get("analytics:repeat-customer-revenue")
    if cached:
        return cached

    result = await db.execute(
        text("SELECT repeat_customer_revenue, repeat_customer_count FROM mv_repeat_customer_revenue")
    )
    row = result.fetchone()
    data = {
        "repeat_customer_revenue": float(row[0]) if row else 0.0,
        "repeat_customer_count": int(row[1]) if row else 0,
    }
    await cache_set("analytics:repeat-customer-revenue", data)
    return data


@router.get("/revenue-trends", response_model=RevenueTrendsResponse)
async def get_revenue_trends(db: AsyncSession = Depends(get_db)):
    """Daily revenue trends for completed orders, sorted ascending by day."""
    cached = await cache_get("analytics:revenue-trends")
    if cached:
        return cached

    result = await db.execute(
        text("SELECT day, daily_revenue, order_count FROM mv_revenue_trends ORDER BY day")
    )
    rows = result.fetchall()
    trends = [
        {
            "day": str(row[0]),
            "daily_revenue": float(row[1]),
            "order_count": int(row[2]),
        }
        for row in rows
    ]
    data = {"trends": trends}
    await cache_set("analytics:revenue-trends", data)
    return data


@router.get("/top-customers", response_model=list[TopCustomerItem])
async def get_top_customers(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top customers by total spend on completed orders."""
    cache_key = f"analytics:top-customers:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        text("SELECT id, name, email, total_spend, order_count FROM mv_top_customers LIMIT :limit"),
        {"limit": limit},
    )
    rows = result.fetchall()
    data = [
        {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "total_spend": float(row[3]),
            "order_count": int(row[4]),
        }
        for row in rows
    ]
    await cache_set(cache_key, data)
    return data
