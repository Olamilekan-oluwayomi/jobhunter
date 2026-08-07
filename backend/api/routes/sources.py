from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import SourceOut
from api.services import list_sources

router = APIRouter(tags=["sources"])


@router.get(
    "/sources",
    response_model=list[SourceOut],
    summary="List sources",
    description=(
        "Lists every known job source together with the number of jobs it has contributed."
    ),
)
def sources(db: Session = Depends(get_db)):
    return list_sources(db)
