-- ============================================================
-- Database Schema for Analytics Backend
-- ============================================================

-- Tables
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(id),
    amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    amount NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- ============================================================
-- Indexes for query optimization
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_refunds_order_id ON refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_status ON orders(customer_id, status);

-- ============================================================
-- Materialized Views for pre-aggregated analytics
-- ============================================================

-- Summary view: all scalar analytics in one row (uses subqueries to avoid JOIN inflation)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_analytics_summary AS
SELECT
    (SELECT COUNT(*) FROM orders) AS total_orders,
    (SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed') AS total_revenue,
    (SELECT COUNT(*) FROM refunds) AS total_refunds,
    (SELECT COALESCE(SUM(amount), 0) FROM refunds) AS total_refund_amount,
    (SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed')
        - (SELECT COALESCE(SUM(amount), 0) FROM refunds) AS net_revenue,
    (SELECT COALESCE(AVG(amount), 0) FROM orders WHERE status = 'completed') AS avg_order_value;

-- Revenue trends: daily completed revenue
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_revenue_trends AS
SELECT
    DATE_TRUNC('day', created_at)::date AS day,
    SUM(amount)                          AS daily_revenue,
    COUNT(id)                            AS order_count
FROM orders
WHERE status = 'completed'
GROUP BY DATE_TRUNC('day', created_at)::date
ORDER BY day;

-- Top customers by spend (top 100)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_customers AS
SELECT
    c.id,
    c.name,
    c.email,
    SUM(o.amount)  AS total_spend,
    COUNT(o.id)    AS order_count
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.status = 'completed'
GROUP BY c.id, c.name, c.email
ORDER BY total_spend DESC
LIMIT 100;

-- Repeat customer revenue (customers with > 1 completed order)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_repeat_customer_revenue AS
SELECT
    SUM(o.amount) AS repeat_customer_revenue,
    COUNT(DISTINCT o.customer_id) AS repeat_customer_count
FROM orders o
WHERE o.status = 'completed'
  AND o.customer_id IN (
      SELECT customer_id
      FROM orders
      WHERE status = 'completed'
      GROUP BY customer_id
      HAVING COUNT(*) > 1
  );

-- ============================================================
-- Function to refresh all materialized views
-- ============================================================

CREATE OR REPLACE FUNCTION refresh_all_views() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_analytics_summary;
    REFRESH MATERIALIZED VIEW mv_revenue_trends;
    REFRESH MATERIALIZED VIEW mv_top_customers;
    REFRESH MATERIALIZED VIEW mv_repeat_customer_revenue;
END;
$$ LANGUAGE plpgsql;
