"""Простая объяснимая оценка Дня 2: правила, без embeddings и вызовов модели."""

from decimal import Decimal

from .models import CompanyProfile, NewsItem, RelevanceAssessment, ScoreFactor


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())


def rank_news(company: CompanyProfile, news: list[NewsItem]) -> list[RelevanceAssessment]:
    """Оценка 0–100 — сумма весов, а не вероятность или обученная метрика.

    Сортировка стабильна: при равном балле остаётся исходный порядок новостей.
    Отсутствующие признаки не подменяем отрицательными значениями.
    """
    assessments = []
    for event in news:
        factors = []

        def add(points: int, text: str, *fields: str) -> None:
            factors.append(ScoreFactor(
                points=points, text=text, company_fields=list(fields), source_ids=[event.id],
            ))

        if company.id in event.company_ids:
            add(60, "В событии явно упоминается идентификатор компании.", "id")
        if set(company.counterparty_ids) & set(event.company_ids):
            add(50, "Событие касается известного контрагента компании.", "counterparty_ids")

        if company.industry_code and event.industry_codes:
            # Сопоставляем полный ОКВЭД или его двухзначный раздел: 28 и 28.29.
            code = company.industry_code.strip()
            match = any(code == target or code.split(".")[0] == target.split(".")[0]
                        for target in event.industry_codes)
            add(35 if match else 0,
                "Отрасль события совпадает с ОКВЭД компании." if match else
                "Отрасль события отличается от указанного ОКВЭД компании.", "industry_code")

        company_regions = [*company.operating_regions, *([company.region] if company.region else [])]
        if event.regions and company_regions:
            match = bool({_normalize(r) for r in company_regions} & {_normalize(r) for r in event.regions})
            fields = (["region"] if company.region else []) + (["operating_regions"] if company.operating_regions else [])
            add(40 if match else 0,
                "Событие относится к известному региону компании." if match else
                "Указанные регионы компании и события не совпадают.", *fields)

        if event.event_type in ("key_rate_unchanged", "credit_conditions"):
            if company.has_loans is not None:
                add(40 if company.has_loans else 0,
                    "У компании есть кредитные продукты." if company.has_loans else
                    "По профилю кредитные продукты отсутствуют.", "has_loans")
            if company.debt_rub is not None:
                debt = Decimal(company.debt_rub)
                if debt > 0 and company.has_loans is not False:
                    if company.has_loans is None:
                        add(40, "В профиле указана положительная сумма долга.", "debt_rub")
                    if company.revenue_rub is not None and Decimal(company.revenue_rub) > 0:
                        ratio = debt / Decimal(company.revenue_rub)
                        add(10 if ratio >= Decimal("0.5") else 5,
                            f"Отношение указанного долга к годовой выручке: {ratio:.2f}; это ориентир, не оценка обслуживания долга.",
                            "debt_rub", "revenue_rub")

        if event.event_type in ("key_rate_unchanged", "deposit_conditions") and company.has_deposits is not None:
            add(25 if company.has_deposits else 0,
                "У компании есть депозитные продукты." if company.has_deposits else
                "По профилю депозитные продукты отсутствуют.", "has_deposits")

        if event.event_type == "fx_change" and company.has_foreign_trade is not None:
            add(35 if company.has_foreign_trade else 0,
                "У компании указана внешнеэкономическая деятельность." if company.has_foreign_trade else
                "Внешнеэкономическая деятельность в профиле не указана как действующая.", "has_foreign_trade")

        score = min(100, sum(factor.points for factor in factors))
        level = "unknown" if not factors else "high" if score >= 40 else "medium" if score >= 20 else "low"
        assessments.append(RelevanceAssessment(event_id=event.id, score=score, level=level, factors=factors))
    return sorted(assessments, key=lambda assessment: -assessment.score)
