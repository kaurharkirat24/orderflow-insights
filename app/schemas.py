"""
Pydantic response models for the analytics API endpoints.
"""

from pydantic import BaseModel


class TotalOrdersResponse(BaseModel):
    total_orders: int


class TotalRevenueResponse(BaseModel):
    total_revenue: float


class TotalRefundsResponse(BaseModel):
    total_refunds: int
    total_refund_amount: float


class NetRevenueResponse(BaseModel):
    net_revenue: float


class AvgOrderValueResponse(BaseModel):
    avg_order_value: float


class RepeatCustomerRevenueResponse(BaseModel):
    repeat_customer_revenue: float
    repeat_customer_count: int


class RevenueTrendItem(BaseModel):
    day: str
    daily_revenue: float
    order_count: int


class RevenueTrendsResponse(BaseModel):
    trends: list[RevenueTrendItem]


class TopCustomerItem(BaseModel):
    id: str
    name: str
    email: str
    total_spend: float
    order_count: int


class HealthResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool


class IngestResponse(BaseModel):
    status: str
