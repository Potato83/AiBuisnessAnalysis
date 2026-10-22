from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from data.models.models import Company
from data.models.shemas import CompanySchema
from backend.database.company import get_db

router = APIRouter(
    prefix="/api/v1/Company",
    tags=["Company"],
)

@router.get("/", response_model=list[CompanySchema])
def get_Company(db: Session = Depends(get_db)):
    return db.query(Company).all()


@router.get("/{company_id}", response_model=CompanySchema)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(
        Company.id == company_id
    ).first()

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Компания не найдена",
        )

    return company

@router.get("/{company_id}/insights", response_model=CompanySchema)
def get_company_insights():
    pass