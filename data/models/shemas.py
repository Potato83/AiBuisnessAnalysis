from pydantic import BaseModel, ConfigDict


class CompanySchema(BaseModel):
    synthetic_u: str
    org_type: str | None = None
    okfs_name: str | None = None
    company_age_years_gradation: str | None = None
    eco_mark_label: str | None = None
    mainokved_code: str | None = None
    mainokved_name: str | None = None
    negativemark: str | None = None
    amount_workers_fns_gradation: str | None = None
    amount_workers_spark_gradation: str | None = None
    cl_type: str | None = None
    cl_product_rko_mark: str | None = None
    cl_product_gar_mark: str | None = None
    cl_product_loa_mark: str | None = None
    cl_product_lea_mark: str | None = None
    cl_product_dep_mark: str | None = None
    cl_product_zpp_mark: str | None = None
    fts_flag: str | None = None
    fts_country_name: str | None = None
    factoring_mark: str | None = None
    revenue_company: float | None = None
    group_id: str | None = None
    city: str | None = None
    region: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaymentSchema(BaseModel):
    id: int
    payer: str
    beneficiary: str
    pay_amt: float | None = None
    pay_cnt: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonSchema(BaseModel):
    id: int
    synthetic_f: str
    city_name: str | None = None
    rc_name: str | None = None
    synthetic_u: str

    model_config = ConfigDict(from_attributes=True)