from data.initilization.init_db import Base

from sqlalchemy import (
    Column, Integer, String, Text, Float, ForeignKey,
)
from sqlalchemy.orm import relationship


class Company(Base):
    __tablename__ = "companies"

    synthetic_u = Column(String, primary_key=True)
    org_type = Column(Text)
    okfs_name = Column(Text)
    company_age_years_gradation = Column(Text)
    eco_mark_label = Column(Text)
    mainokved_code = Column(Text)
    mainokved_name = Column(Text)
    negativemark = Column(Text)
    amount_workers_fns_gradation = Column(Text)
    amount_workers_spark_gradation = Column(Text)
    cl_type = Column(Text)
    cl_product_rko_mark = Column(Text)
    cl_product_gar_mark = Column(Text)
    cl_product_loa_mark = Column(Text)
    cl_product_lea_mark = Column(Text)
    cl_product_dep_mark = Column(Text)
    cl_product_zpp_mark = Column(Text)
    fts_flag = Column(Text)
    fts_country_name = Column(Text)
    factoring_mark = Column(Text)
    revenue_company = Column(Float)
    group_id = Column(Text)
    city = Column(Text)
    region = Column(Text)
    persons = relationship("Person", back_populates="company", cascade="all, delete-orphan")
    payments_sent = relationship("Payment", foreign_keys="Payment.payer", back_populates="payer_company")
    payments_received = relationship("Payment", foreign_keys="Payment.beneficiary", back_populates="beneficiary_company")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    payer = Column(String, ForeignKey("companies.synthetic_u"), nullable=False, index=True)
    beneficiary = Column(String, ForeignKey("companies.synthetic_u"), nullable=False, index=True)

    pay_amt = Column(Float)
    pay_cnt = Column(Integer)

    payer_company = relationship("Company", foreign_keys=[payer], back_populates="payments_sent")
    beneficiary_company = relationship("Company", foreign_keys=[beneficiary], back_populates="payments_received")


class Person(Base):

    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    synthetic_f = Column(String, unique=True, index=True)
    city_name = Column(Text)
    rc_name = Column(Text)

    synthetic_u = Column(
        String, ForeignKey("companies.synthetic_u"),
        nullable=False, index=True,
    )

    company = relationship("Company", back_populates="persons")