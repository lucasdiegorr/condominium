"""Chart-of-accounts routes (financial spec)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.permissions import PERM_CHART_ACCOUNTS_MANAGE, PERM_FINANCIAL_READ
from app.db import get_db
from app.schemas.financial import CategoryCreate, CategoryUpdate, CategoryView
from app.services import financial_service

router = APIRouter(prefix="/chart-accounts", tags=["chart-accounts"])


@router.get("", response_model=list[CategoryView])
async def list_categories(
    scope=Depends(require_permission(PERM_FINANCIAL_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[CategoryView]:
    return await financial_service.list_chart(session, scope)


@router.post("", response_model=CategoryView, status_code=201)
async def create_category(
    body: CategoryCreate,
    scope=Depends(require_permission(PERM_CHART_ACCOUNTS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> CategoryView:
    return await financial_service.create_category(session, scope, name=body.name, kind=body.kind)


@router.patch("/{category_id}", response_model=CategoryView)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    scope=Depends(require_permission(PERM_CHART_ACCOUNTS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> CategoryView:
    return await financial_service.update_category(
        session, scope, category_id, name=body.name, kind=body.kind
    )
