"""Заранее описанные условные сценарии, явно маркируемые как MOCK."""

from decimal import Decimal

from .models import InsightDraft, InsightInput, Reason
from .ranking import rank_news


# В каждом кортеже: возможное влияние, риск и направление дополнительного анализа.
# Это тестовые шаблоны, а не результаты модели или экспертная позиция банка.
SCENARIOS = {
    "credit_conditions": (
        "Условия нового финансирования могут изменить стоимость оборотных средств и инвестиций.",
        "Нужно проверить сроки рефинансирования и договорные ставки.",
        "Можно сравнить доступные условия финансирования.",
    ),
    "deposit_conditions": (
        "Изменение условий размещения средств может повлиять на доходность свободной ликвидности.",
        "Текущие и новые договоры могут иметь разные условия.",
        "Можно сопоставить сроки депозитов с платёжным календарём.",
    ),
    "industry_demand": (
        "Событие в отрасли может изменить спрос на продукцию компании и загрузку мощностей.",
        "Возможны отклонения спроса от плана; нужны данные о портфеле заказов.",
        "Можно проверить возможность участия в новых заказах.",
    ),
    "regional_disruption": (
        "Событие в регионе компании может повлиять на поставки, логистику и сроки исполнения.",
        "Возможны задержки операций в затронутом регионе.",
        "Можно оценить альтернативные маршруты и резервы.",
    ),
    "regulation": (
        "Отраслевые изменения требований могут повлиять на процессы и затраты компании.",
        "Нужно уточнить применимость требований и сроки перехода.",
        "Можно заранее оценить план адаптации процессов.",
    ),
    "counterparty_event": (
        "Событие у связанной компании может передаваться через расчёты или цепочку поставок.",
        "Нужно проверить зависимость от контрагента и незавершённые обязательства.",
        "Можно пересмотреть резервные поставки и условия расчётов.",
    ),
    "fx_change": (
        "Валютные изменения могут повлиять на расчёты по внешнеэкономическим операциям.",
        "Знак и размер эффекта зависят от валюты контрактов и сроков платежей.",
        "Можно сопоставить будущие валютные поступления и платежи.",
    ),
}


class MockClient:
    mode = "mock"
    model_name = None

    def generate(self, request: InsightInput) -> list[InsightDraft]:
        company = request.company_profile
        debt_known = company.debt_rub is not None and Decimal(company.debt_rub) > 0
        rankings = {item.event_id: item for item in (request.rankings or rank_news(company, request.news))}
        results = []
        for event in request.news:
            assessment = rankings[event.id]
            bank = [s for s in request.bank_sources if s.usable_as_bank_view and event.id in s.related_news_ids]
            source_ids = [event.id, *[source.id for source in bank]]
            fields = sorted({field for factor in assessment.factors for field in factor.company_fields})
            explanation = " ".join(factor.text for factor in assessment.factors)
            explanation = explanation or "Недостаточно признаков для оценки связи компании с событием."
            impact = "Влияние не определено; нужны дополнительные сведения о контексте компании."
            risks, opportunities = [], []

            if event.event_type == "key_rate_unchanged":
                # Наличие кредита не раскрывает тип ставки и условия договора.
                if company.has_loans is True or (company.has_loans is None and debt_known):
                    impact = (
                        "При сохранении ставки снижение стоимости нового финансирования может отложиться. "
                        "Влияние на действующие кредиты зависит от их условий; тип ставки неизвестен."
                    )
                    risks = ["Если план зависит от удешевления заёмных средств, его сроки могут измениться."]
                    if company.has_deposits is True:
                        opportunities = ["Доход от размещения средств может частично компенсировать расходы; нужны суммы и сроки."]
                elif company.has_deposits is True:
                    impact = "Влияние на доходность депозитов зависит от договоров; кредитные обязательства оцениваются отдельно."
                    risks = ["Условия продления депозитов могут отличаться от действующих; их нужно уточнить."]
                    opportunities = ["Можно сравнить сроки размещения свободной ликвидности при текущих условиях."]
                elif company.has_loans is False and company.has_deposits is False:
                    impact = "Прямой финансовый канал по этим продуктам слабее; влияние через спрос и контрагентов требует уточнения."
            elif assessment.level in ("high", "medium"):
                impact, risk, opportunity = SCENARIOS.get(event.event_type, (
                    "Указанная связь с компанией требует дополнительного анализа последствий.",
                    "Данных о конкретных обязательствах недостаточно.",
                    "Можно уточнить факторы воздействия.",
                ))
                risks, opportunities = [risk], [opportunity]
            elif assessment.level == "low":
                impact = "Прямое влияние по доступным признакам не подтверждено; косвенные связи требуют уточнения."

            results.append(InsightDraft(
                event_id=event.id,
                relevance=assessment.level,
                reasons=[Reason(text=explanation, company_fields=fields, source_ids=source_ids)],
                impact=impact, risks=risks, opportunities=opportunities,
                ai_interpretation=f"MOCK — демонстрационный сценарий, не ответ LLM. {impact}",
                source_ids=source_ids, confidence="low",
            ))
        return results
