from app.api.deps import get_db
from app.api.schemas.estatisticas import EstatisticasResponse
from app.repositories.estatisticas_repo import EstatisticasRepository
from app.services.estatisticas_service import EstatisticasService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()
svc = EstatisticasService(EstatisticasRepository())


@router.get("/estatisticas", response_model=EstatisticasResponse)
def estatisticas(db: Session = Depends(get_db)):
    payload = svc.get(db)
    return EstatisticasResponse(**payload)
