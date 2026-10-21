from data.initilization.init_db import Base

from sqlalchemy import (
    Column, Integer, String, Text,
)
from sqlalchemy.orm import relationship


class Companies(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    insights = relationship("Insights", back_populates="company", cascade="all, delete-orphan")