"""Refunds paginated endpoint."""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/refunds")
async def get_refunds(page: int = Query(1, ge=1), page_size: int = Query(1000, ge=1, le=10000)):
    from mock_api.main import data_store, paginate
    return paginate(data_store["refunds"], page, page_size)
