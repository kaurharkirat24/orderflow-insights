"""Customers paginated endpoint."""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/customers")
async def get_customers(page: int = Query(1, ge=1), page_size: int = Query(1000, ge=1, le=10000)):
    from mock_api.main import data_store, paginate
    return paginate(data_store["customers"], page, page_size)
