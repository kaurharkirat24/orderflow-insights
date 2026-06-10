# Backend Analytics Service

A high-performance backend service that ingests large volumes of data from multiple APIs, stores and processes data in PostgreSQL, and exposes analytics endpoints with response times consistently below 2 seconds.

## Architecture

The system follows a **4-layer architecture**:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Data       │     │   Mock API   │     │  Ingestion   │     │  Analytics   │
│  Generator    │────▶│  (Port 8001) │────▶│   Service    │────▶│  API (8000)  │
│  (Faker)      │     │  Paginated   │     │  httpx+async │     │  FastAPI     │
└──────────────┘     └──────────────┘     └──────┬───────┘     └──────┬───────┘
                                                  │                    │
                                                  ▼                    ▼
                                          ┌──────────────┐     ┌──────────────┐
                                          │  PostgreSQL   │     │    Redis     │
                                          │  + Mat Views  │     │   Cache      │
                                          └──────────────┘     └──────────────┘
```

### Layer Details

1. **Data Generator** (`data_generator/generate.py`): Uses Faker with seed 42 to generate reproducible datasets — 100K customers, 1M orders, 200K refunds.

2. **Mock APIs** (`mock_api/`): FastAPI application on port 8001 serving paginated endpoints for customers, orders, and refunds. Loads JSON data into memory at startup.

3. **Ingestion Service** (`ingestion/ingest.py`): Async service using httpx to fetch all pages concurrently (batches of 50), then bulk-inserts into PostgreSQL using asyncpg `COPY` staging tables with `ON CONFLICT DO NOTHING` for idempotency.

4. **Analytics API** (`app/`): FastAPI application on port 8000 with 8 analytics endpoints, all reading from pre-aggregated materialized views and cached in Redis.

## Optimization Decisions

### Materialized Views
Pre-aggregated analytics queries into 4 materialized views, reducing complex JOINs and aggregations from runtime to a one-time computation after ingestion:
- `mv_analytics_summary` — scalar metrics (total orders, revenue, refunds, net revenue, avg order value)
- `mv_revenue_trends` — daily revenue breakdown
- `mv_top_customers` — top 100 customers by spend
- `mv_repeat_customer_revenue` — revenue from repeat customers

### Redis TTL Caching
Every analytics endpoint checks Redis first (60-second TTL). Cache is automatically flushed after each ingestion run to ensure data freshness.

### Async HTTP Ingestion
Uses `httpx.AsyncClient` with `asyncio.gather` to fetch 50 pages concurrently, dramatically reducing ingestion time compared to sequential fetching.

### Bulk Inserts with asyncpg
Uses `asyncpg.copy_records_to_table` into temporary staging tables in batches of 5,000 records, then merges into the final tables with `ON CONFLICT DO NOTHING` for idempotent re-runs.

### Database Indexes
5 targeted indexes on orders and refunds tables to optimize the most common query patterns:
- `idx_orders_customer_id` — customer-order lookups
- `idx_orders_status` — status filtering
- `idx_orders_created_at` — time-range queries
- `idx_refunds_order_id` — refund-order joins
- `idx_orders_customer_status` — composite index for customer+status queries

## Setup Instructions

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+ (for data generation)

### Quick Start

```bash
# 1. Install dependencies (for data generation)
pip install -r requirements.txt

# 2. Generate seed data
python data_generator/generate.py

# 3. Start all services
docker-compose up --build -d

# 4. Wait for services to be healthy (~10 seconds)
sleep 10

# 5. Verify health
curl http://localhost:8000/health

# 6. Trigger data ingestion
curl -X POST http://localhost:8000/ingest

# 7. Wait for ingestion to complete (~2-3 minutes)
# Check logs: docker logs -f analytics_app

# 8. Query analytics
curl http://localhost:8000/analytics/total-orders
curl http://localhost:8000/analytics/total-revenue
curl http://localhost:8000/analytics/total-refunds
curl http://localhost:8000/analytics/net-revenue
curl http://localhost:8000/analytics/avg-order-value
curl http://localhost:8000/analytics/repeat-customer-revenue
curl http://localhost:8000/analytics/revenue-trends
curl "http://localhost:8000/analytics/top-customers?limit=10"
```

### Stopping Services

```bash
docker-compose down        # stop services
docker-compose down -v     # stop services and remove data volumes
```

## API Documentation

### Analytics Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/analytics/total-orders` | GET | Total number of orders |
| `/analytics/total-revenue` | GET | Total revenue from completed orders |
| `/analytics/total-refunds` | GET | Total refund count and amount |
| `/analytics/net-revenue` | GET | Revenue minus refunds |
| `/analytics/avg-order-value` | GET | Average completed order value |
| `/analytics/repeat-customer-revenue` | GET | Revenue from repeat customers |
| `/analytics/revenue-trends` | GET | Daily revenue trends |
| `/analytics/top-customers?limit=N` | GET | Top N customers by spend (max 100) |

### System Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check (PostgreSQL + Redis) |
| `/ingest` | POST | Trigger data ingestion |

### Interactive API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Load Test

### Running the Load Test

```bash
# Warm the cache first
curl http://localhost:8000/analytics/total-orders > /dev/null

# Run Locust
locust -f load_test/locustfile.py \
  --host=http://localhost:8000 \
  --users=50 --spawn-rate=5 \
  --run-time=60s --headless \
  --csv=load_test/results
```

### Load Test Configuration
- **Users**: 50 concurrent
- **Spawn rate**: 5 users/second
- **Duration**: 60 seconds
- **Endpoints**: All 8 analytics endpoints (equal weight) + health check (5% weight)

### Expected Results
- All endpoints p95 < 2000ms
- Error rate < 1%
- Results saved to `load_test/results_stats.csv`

## Project Structure

```
project/
├── docker-compose.yml          # 4 services: postgres, redis, mock_api, app
├── Dockerfile                  # Analytics app container
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── data_generator/
│   └── generate.py             # Seed data generation (Faker)
├── data/                       # Generated JSON files (gitignored)
├── mock_api/
│   ├── Dockerfile              # Mock API container
│   ├── main.py                 # FastAPI app with pagination
│   └── routers/                # Paginated endpoints
├── ingestion/
│   └── ingest.py               # Async ingestion with httpx + asyncpg
├── app/
│   ├── main.py                 # Analytics FastAPI app
│   ├── database.py             # SQLAlchemy async engine
│   ├── models.py               # ORM models
│   ├── cache.py                # Redis helpers
│   ├── schemas.py              # Pydantic response models
│   └── routers/
│       └── analytics.py        # 8 analytics endpoints
├── migrations/
│   └── init.sql                # DDL + indexes + materialized views
└── load_test/
    └── locustfile.py           # Locust load test
```

## Tech Stack

- **Python 3.11** — application runtime
- **FastAPI** — web framework for both mock APIs and analytics
- **PostgreSQL 15** — primary data store with materialized views
- **Redis 7** — response caching layer
- **httpx** — async HTTP client for ingestion
- **asyncpg** — high-performance async PostgreSQL driver
- **SQLAlchemy 2.0** — ORM for analytics queries
- **Faker** — reproducible test data generation
- **Locust** — load testing framework
- **Docker + Docker Compose** — containerization and orchestration
