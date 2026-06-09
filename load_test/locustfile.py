"""
Load Test — Locust configuration for analytics endpoints.

Tests all 8 analytics endpoints with equal weight,
plus a 5% weight health check endpoint.

Run with:
    locust -f load_test/locustfile.py --host=http://localhost:8000 \
           --users=50 --spawn-rate=5 --run-time=60s --headless \
           --csv=load_test/results
"""

from locust import HttpUser, task, between


class AnalyticsUser(HttpUser):
    """Simulates a user hitting analytics endpoints."""

    wait_time = between(0.5, 2.0)

    @task(10)
    def total_orders(self):
        self.client.get("/analytics/total-orders")

    @task(10)
    def total_revenue(self):
        self.client.get("/analytics/total-revenue")

    @task(10)
    def total_refunds(self):
        self.client.get("/analytics/total-refunds")

    @task(10)
    def net_revenue(self):
        self.client.get("/analytics/net-revenue")

    @task(10)
    def avg_order_value(self):
        self.client.get("/analytics/avg-order-value")

    @task(10)
    def repeat_customer_revenue(self):
        self.client.get("/analytics/repeat-customer-revenue")

    @task(10)
    def revenue_trends(self):
        self.client.get("/analytics/revenue-trends")

    @task(10)
    def top_customers(self):
        self.client.get("/analytics/top-customers?limit=10")

    @task(1)
    def health(self):
        self.client.get("/health")
