from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db


def make_crud_router(
    *,
    model: type,
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    out_schema: type[BaseModel],
    prefix: str,
    tag: str,
    write_permission: str | None = None,
    order_by: list | None = None,
) -> APIRouter:
    """Standard list/get/create/update router for a master-data entity.

    Master data is deactivated (`is_active=False`), never hard-deleted, since
    other tables hold foreign keys into it — so there's no DELETE route.
    """
    router = APIRouter(prefix=prefix, tags=[tag])
    write_dep = Depends(require_permission(write_permission)) if write_permission else Depends(get_current_user)

    @router.get("", response_model=list[out_schema])
    def list_items(db: Session = Depends(get_db), _user=Depends(get_current_user)):
        query = select(model)
        if order_by:
            query = query.order_by(*order_by)
        return db.execute(query).scalars().all()

    @router.get("/{item_id}", response_model=out_schema)
    def get_item(item_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        obj = db.get(model, item_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{tag} not found")
        return obj

    @router.post("", response_model=out_schema, status_code=status.HTTP_201_CREATED)
    def create_item(payload: create_schema, db: Session = Depends(get_db), _user=write_dep):
        obj = model(**payload.model_dump())
        db.add(obj)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflicts with an existing record")
        db.refresh(obj)
        return obj

    @router.put("/{item_id}", response_model=out_schema)
    def update_item(
        item_id: int, payload: update_schema, db: Session = Depends(get_db), _user=write_dep
    ):
        obj = db.get(model, item_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{tag} not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflicts with an existing record")
        db.refresh(obj)
        return obj

    return router
