from datetime import date
from typing import Callable, Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile, status
from starlette.responses import StreamingResponse

from app.api.routes.auth import require_current_user
from app.api.schemas import (
    CounterpartyCreate,
    CounterpartyListResponse,
    CounterpartyResponse,
    CounterpartyUpdate,
    CounterpartyUploadResponse,
)
from app.core.config import settings
from app.core.dependencies import InternalDependencies
from app.domain.models.user import User
from app.logging.utils import log_exception


def register_counterparty_routes(
    app: FastAPI,
    provide_dependencies: Callable[[], Iterator[InternalDependencies]],
):
    router = APIRouter(prefix="/counterparties", tags=["counterparties"])

    @router.post(
        "",
        response_model=CounterpartyResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_counterparty(
        counterparty_data: CounterpartyCreate,
        internal: InternalDependencies = Depends(provide_dependencies),
        current_user: User = Depends(require_current_user),
    ):
        try:
            existing = internal.counterparty_service.get_counterparty_by_name(counterparty_data.name, current_user.id)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Counterparty with name '{counterparty_data.name}' already exists",
                )

            return internal.counterparty_service.create_counterparty(
                counterparty_data.name, current_user.id, counterparty_data.type
            )
        except HTTPException:
            raise
        except Exception as e:
            log_exception("Error creating counterparty: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error creating counterparty: {str(e)}",
            )

    @router.get("", response_model=CounterpartyListResponse)
    async def get_all_counterparties(
        internal: InternalDependencies = Depends(provide_dependencies),
        current_user: User = Depends(require_current_user),
    ):
        try:
            counterparties = internal.counterparty_service.get_all_counterparties(current_user.id)
            return CounterpartyListResponse(counterparties=counterparties, total=len(counterparties))
        except Exception as e:
            log_exception("Error retrieving counterparties: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error retrieving counterparties: {str(e)}",
            )

    @router.get("/export")
    async def export_counterparties(
        internal: InternalDependencies = Depends(provide_dependencies),
        current_user: User = Depends(require_current_user),
    ):
        counterparties = internal.counterparty_service.get_all_counterparties(current_user.id)

        def escape_csv(value: str) -> str:
            escaped = value.replace('"', '""')
            if "," in escaped or '"' in escaped or "\n" in escaped:
                return f'"{escaped}"'
            return escaped

        rows = ["name,type\n"]
        for counterparty in counterparties:
            rows.append(f"{escape_csv(counterparty.name)},{escape_csv(str(counterparty.type))}\n")

        filename = f"counterparties-{date.today().isoformat()}.csv"
        return StreamingResponse(
            iter(rows),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/{counterparty_id}", response_model=CounterpartyResponse)
    async def get_counterparty(
        counterparty_id: UUID,
        internal: InternalDependencies = Depends(provide_dependencies),
        current_user: User = Depends(require_current_user),
    ):
        try:
            counterparty = internal.counterparty_service.get_counterparty(counterparty_id, current_user.id)
            if not counterparty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Counterparty with ID {counterparty_id} not found",
                )
            return counterparty
        except HTTPException:
            raise
        except Exception as e:
            log_exception("Error retrieving counterparty: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error retrieving counterparty: {str(e)}",
            )

    @router.put("/{counterparty_id}", response_model=CounterpartyResponse)
    async def update_counterparty(
        counterparty_id: UUID,
        counterparty_data: CounterpartyUpdate,
        internal: InternalDependencies = Depends(provide_dependencies),
        current_user: User = Depends(require_current_user),
    ):
        try:
            existing = internal.counterparty_service.get_counterparty(counterparty_id, current_user.id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Counterparty with ID {counterparty_id} not found",
                )

            name_exists = internal.counterparty_service.get_counterparty_by_name(counterparty_data.name, current_user.id)
            if name_exists and name_exists.id != counterparty_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Counterparty with name '{counterparty_data.name}' already exists",
                )

            return internal.counterparty_service.update_counterparty(
                counterparty_id, counterparty_data.name, current_user.id, counterparty_data.type
            )
        except HTTPException:
            raise
        except Exception as e:
            log_exception("Error updating counterparty: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating counterparty: {str(e)}",
            )

    @router.delete(
        "/{counterparty_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_counterparty(
        counterparty_id: UUID,
        internal: InternalDependencies = Depends(provide_dependencies),
        current_user: User = Depends(require_current_user),
    ):
        try:
            existing = internal.counterparty_service.get_counterparty(counterparty_id, current_user.id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Counterparty with ID {counterparty_id} not found",
                )

            internal.counterparty_service.delete_counterparty(counterparty_id, current_user.id)
            return None
        except HTTPException:
            raise
        except Exception as e:
            log_exception("Error deleting counterparty: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error deleting counterparty: {str(e)}",
            )

    @router.post(
        "/upload",
        response_model=CounterpartyUploadResponse,
        status_code=status.HTTP_200_OK,
    )
    async def upload_counterparties_csv(
        file: UploadFile = File(...),
        internal: InternalDependencies = Depends(provide_dependencies),
        current_user: User = Depends(require_current_user),
    ):
        if not file.content_type or not file.content_type.startswith(("text/csv", "application/csv")):
            if not file.filename or not file.filename.lower().endswith(".csv"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be a CSV file",
                )

        content = await file.read()
        csv_content = content.decode("utf-8")

        existing_names = {c.name for c in internal.counterparty_service.get_all_counterparties(current_user.id)}
        counterparties = internal.counterparty_service.upsert_counterparties_from_csv(csv_content, current_user.id)

        updated_count = len([c for c in counterparties if c.name in existing_names])

        return CounterpartyUploadResponse(
            counterparties=counterparties,
            total=len(counterparties),
            created=len(counterparties) - updated_count,
            updated=updated_count,
        )

    app.include_router(router, prefix=settings.API_V1_STR)
