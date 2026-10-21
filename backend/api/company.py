from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from data.models.models import Companies
from data.models.shemas import CompaniesSchema
from backend.database.company import get_db

router = APIRouter(
    prefix="/api/companies",
    tags=["Companies"],
)

@router.get("/", response_model=list[CompaniesSchema])
def get_companies(db: Session = Depends(get_db)):
    return db.query(Companies).all()


@router.get("/{company_id}", response_model=CompaniesSchema)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Companies).filter(
        Companies.id == company_id
    ).first()

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Компания не найдена",
        )

    return company