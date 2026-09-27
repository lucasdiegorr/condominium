"""Resident management routes — persons, unit links and accounts (people spec).

All routes are scoped to the condominium of the scoped token. Management is
performed by the síndico of the condominium and the global administrator;
listing is read for the conselho as well.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.permissions import (
    PERM_RESIDENTS_MANAGE,
    PERM_RESIDENTS_READ,
    PERM_USERS_MANAGE,
)
from app.db import get_db
from app.schemas.people import (
    AccountCreate,
    AccountView,
    PersonCreate,
    PersonUpdate,
    PersonView,
    UnitLinkInput,
)
from app.services import people_service

router = APIRouter(prefix="/residents", tags=["residents"])


@router.get("", response_model=list[PersonView])
async def list_residents(
    scope=Depends(require_permission(PERM_RESIDENTS_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[PersonView]:
    return await people_service.list_roster(session, scope.condominium_id)


@router.post("", response_model=PersonView, status_code=201)
async def create_resident(
    body: PersonCreate,
    scope=Depends(require_permission(PERM_RESIDENTS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> PersonView:
    return await people_service.create_person(
        session,
        scope.condominium_id,
        name=body.name,
        cpf=body.cpf,
        phone=body.phone,
        email_contact=body.email_contact,
    )


@router.get("/{person_id}", response_model=PersonView)
async def get_resident(
    person_id: int,
    scope=Depends(require_permission(PERM_RESIDENTS_READ)),
    session: AsyncSession = Depends(get_db),
) -> PersonView:
    person = await people_service.get_person_detail(session, scope.condominium_id, person_id)
    return person


@router.patch("/{person_id}", response_model=PersonView)
async def update_resident(
    person_id: int,
    body: PersonUpdate,
    scope=Depends(require_permission(PERM_RESIDENTS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> PersonView:
    return await people_service.update_person(
        session,
        scope.condominium_id,
        person_id,
        name=body.name,
        phone=body.phone,
        email_contact=body.email_contact,
    )


@router.post("/{person_id}/links", response_model=PersonView, status_code=201)
async def add_resident_link(
    person_id: int,
    body: UnitLinkInput,
    scope=Depends(require_permission(PERM_RESIDENTS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> PersonView:
    return await people_service.add_unit_link(
        session,
        scope.condominium_id,
        person_id,
        role=body.role,
        unit_id=body.unit_id,
    )


@router.delete("/{person_id}/links/{link_id}", response_model=PersonView)
async def remove_resident_link(
    person_id: int,
    link_id: int,
    scope=Depends(require_permission(PERM_RESIDENTS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> PersonView:
    return await people_service.remove_unit_link(session, scope.condominium_id, person_id, link_id)


@router.post("/{person_id}/account", response_model=AccountView, status_code=201)
async def create_person_account(
    person_id: int,
    body: AccountCreate,
    scope=Depends(require_permission(PERM_USERS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> AccountView:
    return await people_service.create_account(
        session,
        scope.condominium_id,
        person_id,
        email=body.email,
        password=body.password,
    )
