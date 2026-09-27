"""Administrator routes — role management, condominium CRUD and associations.

The global administrator operates here. Per-condominium operations require a
scoped token for that condominium (after selection); listing and creating
condominiums only require the identity token.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    current_global_admin,
    require_permission,
    require_scope_matches,
)
from app.core.permissions import (
    PERM_CONDOMINIUMS_MANAGE,
    PERM_MEMBERSHIPS_MANAGE,
    PERM_ROLES_MANAGE,
)
from app.db import get_db
from app.models import User
from app.schemas.admin import (
    AssociationUpdate,
    AssociationView,
    CondominiumCreate,
    CondominiumUpdate,
    CondominiumView,
    FunctionRolesUpdate,
    RoleOverview,
    UnitLinkCreate,
)
from app.services import condominium_service, roles_service

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Role management (access-control) ---


@router.get(
    "/condominiums/{condominium_id}/roles",
    response_model=RoleOverview,
)
async def list_roles(
    condominium_id: int,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_ROLES_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> RoleOverview:
    return await roles_service.list_role_overview(session, condominium_id)


@router.put(
    "/condominiums/{condominium_id}/users/{user_id}/functions",
    response_model=RoleOverview,
)
async def set_functions(
    condominium_id: int,
    user_id: int,
    body: FunctionRolesUpdate,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_ROLES_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> RoleOverview:
    return await roles_service.set_function_roles(session, condominium_id, user_id, body.roles)


@router.post(
    "/condominiums/{condominium_id}/people/{person_id}/links",
    response_model=RoleOverview,
)
async def add_unit_link(
    condominium_id: int,
    person_id: int,
    body: UnitLinkCreate,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_ROLES_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> RoleOverview:
    return await roles_service.create_unit_link(
        session, condominium_id, person_id, body.role, body.unit_id
    )


@router.delete(
    "/condominiums/{condominium_id}/links/{link_id}",
    response_model=RoleOverview,
)
async def remove_unit_link(
    condominium_id: int,
    link_id: int,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_ROLES_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> RoleOverview:
    await roles_service.delete_unit_link(session, condominium_id, link_id)
    return await roles_service.list_role_overview(session, condominium_id)


# --- Condominium CRUD (condominium-management) ---


@router.get("/condominiums", response_model=list[CondominiumView])
async def list_condominiums(
    _admin: User = Depends(current_global_admin),
    session: AsyncSession = Depends(get_db),
) -> list[CondominiumView]:
    return [CondominiumView.model_validate(c) for c in await condominium_service.list_all(session)]


@router.post("/condominiums", response_model=CondominiumView, status_code=201)
async def create_condominium(
    body: CondominiumCreate,
    _admin: User = Depends(current_global_admin),
    session: AsyncSession = Depends(get_db),
) -> CondominiumView:
    condominium = await condominium_service.create(session, body.name, body.address)
    return CondominiumView.model_validate(condominium)


@router.patch("/condominiums/{condominium_id}", response_model=CondominiumView)
async def update_condominium(
    condominium_id: int,
    body: CondominiumUpdate,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_CONDOMINIUMS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> CondominiumView:
    condominium = await condominium_service.get_or_404(session, condominium_id)
    condominium = await condominium_service.update(session, condominium, body.name, body.address)
    return CondominiumView.model_validate(condominium)


@router.delete("/condominiums/{condominium_id}", status_code=204)
async def deactivate_condominium(
    condominium_id: int,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_CONDOMINIUMS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> None:
    condominium = await condominium_service.get_or_404(session, condominium_id)
    await condominium_service.deactivate(session, condominium)
    return None


# --- User - condominium associations ---


@router.get(
    "/condominiums/{condominium_id}/associations",
    response_model=list[AssociationView],
)
async def list_associations(
    condominium_id: int,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_MEMBERSHIPS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> list[AssociationView]:
    return await condominium_service.list_associations(session, condominium_id)


@router.put(
    "/condominiums/{condominium_id}/associations/{user_id}",
    response_model=AssociationView,
)
async def set_association(
    condominium_id: int,
    user_id: int,
    body: AssociationUpdate,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_MEMBERSHIPS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> AssociationView:
    return await condominium_service.set_association(session, condominium_id, user_id, body.active)


@router.delete("/condominiums/{condominium_id}/associations/{user_id}", status_code=204)
async def remove_association(
    condominium_id: int,
    user_id: int,
    _scope=Depends(require_scope_matches),
    _permission=Depends(require_permission(PERM_MEMBERSHIPS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> None:
    await condominium_service.remove_association(session, condominium_id, user_id)
    return None
