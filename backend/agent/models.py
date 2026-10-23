"""Контракты AI-модуля. Здесь нет моделей БД или HTTP-маршрутов."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator


# Названия из приложения 3 кейса. Технический ID хранится в адаптере провайдера.
ALLOWED_MODELS = (
    "Gemma 4 26B A4B",
    "GLM-5.3-Flash",
    "Qwen3.6 35B A3B",
    "DeepSeek-V4.1-Flash",
    "Qwen3-VL-30B-A3B-Instruct",
    "Kimi-K2.6",
)

Text = Annotated[str, Field(min_length=1, strict=True)]
Money = Annotated[str, Field(pattern=r"^\d+(\.\d+)?$", strict=True)]


class Contract(BaseModel):
    # Reject misspelled fields rather than quietly losing client context.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CompanyProfile(Contract):
    """Нормализованный профиль: адаптацию ORM/CSV выполняет вызывающий код.

    Деньги передаются строкой в рублях. Пустые признаки остаются None.
    Долг и выручка должны иметь одинаковую валюту и согласованный период оценки.
    """
    id: Text
    name: Text | None = None
    industry_code: Text | None = None
    industry_name: Text | None = None
    region: Text | None = None
    revenue_rub: Money | None = None
    debt_rub: Money | None = None
    # None — признак неизвестен, а не отсутствует. Это важно для неполных данных.
    has_loans: Annotated[bool, Field(strict=True)] | None = None
    has_deposits: Annotated[bool, Field(strict=True)] | None = None
    has_foreign_trade: Annotated[bool, Field(strict=True)] | None = None
    operating_regions: list[Text] = Field(default_factory=list)
    counterparty_ids: list[Text] = Field(default_factory=list)


class Source(Contract):
    id: Text
    title: Text
    url: HttpUrl | None = None
    published_at: AwareDatetime | None = None
    is_synthetic: bool = False


class NewsItem(Source):
    text: Text
    # Метки передаёт news-компонент. Не пытаемся угадывать их по подстрокам текста.
    event_type: Literal[
        "key_rate_unchanged", "credit_conditions", "deposit_conditions",
        "industry_demand", "regional_disruption", "regulation",
        "counterparty_event", "fx_change", "other",
    ] = "other"
    industry_codes: list[Text] = Field(default_factory=list)
    regions: list[Text] = Field(default_factory=list)
    company_ids: list[Text] = Field(default_factory=list)


class BankSource(Source):
    text: Text
    # Явное подтверждение происхождения вызывающим компонентом, не оценка LLM.
    # Для bank_view также необходим URL и отсутствие флага is_synthetic.
    verified: Annotated[bool, Field(strict=True)] = False
    related_news_ids: list[Text] = Field(default_factory=list)

    @property
    def usable_as_bank_view(self) -> bool:
        return self.verified and not self.is_synthetic and self.url is not None


class ScoreFactor(Contract):
    text: Text
    company_fields: list[Text]
    source_ids: list[Text]
    points: int = Field(ge=0, le=100)


class RelevanceAssessment(Contract):
    event_id: Text
    score: int = Field(ge=0, le=100)
    level: Literal["high", "medium", "low", "unknown"]
    factors: list[ScoreFactor]


class InsightInput(Contract):
    company_profile: CompanyProfile
    news: list[NewsItem]
    bank_sources: list[BankSource]
    # Внутреннее поле: рассчитывается фасадом перед вызовом клиента.
    rankings: list[RelevanceAssessment] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_ids(self) -> "InsightInput":
        ids = [source.id for source in [*self.news, *self.bank_sources]]
        if len(ids) != len(set(ids)):
            raise ValueError("Source IDs must be unique across news and bank_sources")
        news_ids = {item.id for item in self.news}
        for source in self.bank_sources:
            if not set(source.related_news_ids) <= news_ids:
                raise ValueError("related_news_ids must refer to supplied news")
        return self


class Reason(Contract):
    text: Text
    company_fields: list[Text] = Field(default_factory=list)
    source_ids: list[Text] = Field(min_length=1)


class InsightDraft(Contract):
    """Small provider output; IDs, source metadata and bank quotes are added locally."""

    event_id: Text
    relevance: Literal["high", "medium", "low", "unknown"]
    reasons: list[Reason] = Field(min_length=1)
    impact: Text
    risks: list[Text]
    opportunities: list[Text]
    ai_interpretation: Text
    source_ids: list[Text] = Field(min_length=1)
    confidence: Literal["low", "medium", "high"] = "low"


class CitedSource(Source):
    kind: Literal["external_news", "bank_analysis"]


class TokenUsage(Contract):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class GenerationBatch(Contract):
    items: list[InsightDraft]
    usage: TokenUsage | None = None
    provider_model: Text | None = None


class InsightTrace(Contract):
    ranking_version: Literal["rules-v1"] = "rules-v1"
    company_fields: dict[str, object]
    ranking_factors: list[ScoreFactor]
    source_ids: list[Text]
    bank_source_ids: list[Text]
    steps: list[Text]


class RunTrace(Contract):
    attempted_mode: Literal["mock", "llm"]
    attempted_model: Text | None
    fallback_reason: Text | None = None
    ranked_news_ids: list[Text]
    excluded_bank_source_ids: list[Text]
    usage: TokenUsage | None = None
    provider_model: Text | None = None


class Insight(InsightDraft):
    id: Text
    company_id: Text
    headline: Text
    # Caller-supplied event description, not independently verified facts.
    facts: list[Text]
    why_relevant: Text
    # Bank text is copied from selected inputs, never invented by a mock or LLM.
    bank_view: Text | None
    sources: list[CitedSource]
    agent_run_id: Text
    generated_at: AwareDatetime
    is_mock: bool
    relevance_score: int = Field(ge=0, le=100)
    rank: int = Field(ge=1)
    trace: InsightTrace


class InsightResult(Contract):
    schema_version: Literal["1.0"] = "1.0"
    mode: Literal["mock", "llm"]
    model: Text | None
    agent_run_id: Text
    generated_at: AwareDatetime
    company_id: Text
    items: list[Insight]
    total: int = Field(ge=0)
    warnings: list[str]
    trace: RunTrace
