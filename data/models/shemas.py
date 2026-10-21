from pydantic import BaseModel, ConfigDict


class CompaniesSchema(BaseModel):
    id: int
    name: str
    industry: str | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)