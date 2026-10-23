"""День 2: вход -> ранжирование -> один клиент -> проверка ссылок -> JSON и trace.

Полноценная агентная самопроверка остаётся на День 3. Fallback включается явно.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import TypeAdapter

from .mock import MockClient
from .config import read_settings
from .llm import LLMError, APIMiraClient
from .ranking import rank_news
from .models import (
    ALLOWED_MODELS, CitedSource, GenerationBatch, Insight, InsightDraft,
    InsightInput, InsightResult, InsightTrace, RunTrace,
)


class InsightClient(Protocol):
    """Единственный контракт клиента генерации: MockClient или APIMiraClient.

    Адаптер отвечает за prompt, таймауты, лимиты токенов и ошибки API.
    model_name — название из кейса; технический ID провайдера задаётся в адаптере.
    generate возвращает список черновиков либо JSON-массив черновиков.
    """

    mode: Literal["mock", "llm"]
    model_name: str | None

    def generate(self, request: InsightInput) -> list[InsightDraft] | str | GenerationBatch: ...


def _validated_batch(client: InsightClient, request: InsightInput) -> GenerationBatch:
    """Структурные ошибки проверяем до выбора fallback и до сборки ответа."""
    if not request.news:
        return GenerationBatch(items=[])
    raw = client.generate(request)
    if isinstance(raw, GenerationBatch):
        batch = raw
    else:
        adapter = TypeAdapter(list[InsightDraft])
        drafts = adapter.validate_json(raw) if isinstance(raw, str) else adapter.validate_python(raw)
        batch = GenerationBatch(items=drafts)
    events = {event.id: event for event in request.news}
    if len(batch.items) != len(events) or {d.event_id for d in batch.items} != set(events):
        raise ValueError("Client must return exactly one draft for each supplied news item")
    company = request.company_profile.model_dump()
    for draft in batch.items:
        ids = set(draft.source_ids)
        allowed = {draft.event_id, *[
            s.id for s in request.bank_sources if draft.event_id in s.related_news_ids
        ]}
        if draft.event_id not in ids or not ids <= allowed:
            raise ValueError("Draft must cite its news and only associated supplied bank sources")
        if len(ids) != len(draft.source_ids):
            raise ValueError("Draft source_ids must not contain duplicates")
        for reason in draft.reasons:
            if not set(reason.source_ids) <= ids:
                raise ValueError("Reason citations must be included in draft source_ids")
            for field in reason.company_fields:
                if field not in company or company[field] is None or company[field] == []:
                    raise ValueError("Reason must reference a known, populated company field")
    return batch


def generate_insights(
    company_profile: dict[str, Any],
    news: list[dict[str, Any]],
    bank_sources: list[dict[str, Any]],
    *,
    client: InsightClient | None = None,
    mode: Literal["mock", "llm"] | None = None,
    fallback_to_mock: bool = False,
) -> dict[str, Any]:
    """Возвращает JSON-совместимый dict. Режим берётся из .env/окружения.

    ValidationError: нарушена схема. ValueError: несогласованные ссылки/настройки.
    Без явного fallback_to_mock=True ошибки LLM передаются вызывающему коду.
    На каждую новость возвращается один ранжированный результат, включая unknown.
    HTTP, хранение результата, повторы и отображение остаются задачами backend.
    """
    request = InsightInput.model_validate({
        "company_profile": company_profile, "news": news, "bank_sources": bank_sources,
    })
    requested_mode = mode if mode is not None else (client.mode if client is not None else read_settings().get("AGENT_MODE", "mock"))
    if requested_mode not in ("mock", "llm"):
        raise ValueError("Client mode must be mock or llm")
    if client is not None:
        if client.mode != requested_mode:
            raise ValueError("Explicit mode must match client.mode")
        if client.mode == "llm" and client.model_name not in ALLOWED_MODELS:
            raise ValueError("LLM must be in case appendix 3 allowlist")
        if client.mode == "mock" and client.model_name is not None:
            raise ValueError("A mock must not claim to use a language model")

    rankings = rank_news(request.company_profile, request.news)
    events = {event.id: event for event in request.news}
    # Происхождение банковского текста подтверждает вызывающий компонент.
    # Неподтверждённые/синтетические выдержки не попадают даже в prompt модели.
    excluded_bank = [s.id for s in request.bank_sources if not s.usable_as_bank_view]
    prepared = request.model_copy(update={
        "news": [events[rank.event_id] for rank in rankings],
        "bank_sources": [s for s in request.bank_sources if s.usable_as_bank_view],
        "rankings": rankings,
    })
    attempted_model = client.model_name if client is not None else (
        APIMiraClient.model_name if requested_mode == "llm" else None
    )
    fallback_reason = None
    try:
        if client is not None:
            selected = client
        elif requested_mode == "llm":
            selected = APIMiraClient.from_env()
        else:
            selected = MockClient()
        batch = _validated_batch(selected, prepared)
    except (LLMError, ValueError) as error:
        if requested_mode != "llm" or not fallback_to_mock:
            raise
        # Маркируем подмену на уровне всего запуска; смешанных LLM/mock пачек нет.
        fallback_reason = type(error).__name__
        selected = MockClient()
        batch = _validated_batch(selected, prepared)

    drafts = {draft.event_id: draft for draft in batch.items}
    bank = {source.id: source for source in request.bank_sources}
    known_sources = {**events, **bank}
    company = request.company_profile.model_dump()
    run_id = f"run-{uuid4().hex}"
    generated_at = datetime.now(timezone.utc)
    warnings = []
    if selected.mode == "mock":
        warnings.append("MOCK: LLM не подключена; результат предназначен для проверки интеграции.")
    if fallback_reason:
        warnings.append(f"FALLBACK: LLM не дала валидного результата ({fallback_reason}); использован MOCK.")
    if excluded_bank:
        warnings.append("Неподтверждённые или синтетические банковские материалы исключены: " + ", ".join(excluded_bank))
    if any(source.is_synthetic for source in known_sources.values()):
        warnings.append("Вход содержит синтетические материалы; это не реальные новости или позиция банка.")

    items = []
    for position, assessment in enumerate(rankings, 1):
        draft = drafts[assessment.event_id]
        event = events[draft.event_id]
        cited_bank = [bank[id_] for id_ in draft.source_ids if id_ in bank]
        if not cited_bank:
            warnings.append(f"{event.id}: связанная аналитика банка не использована; позиция банка отсутствует.")
        used_fields = sorted({
            field for reason in [*assessment.factors, *draft.reasons] for field in reason.company_fields
        })
        steps = ["validate_input", "rank_news", "fallback_mock" if fallback_reason else f"generate_{selected.mode}",
                 "validate_output", "assemble_sources"]
        draft_data = draft.model_dump()
        # Численная оценка и порядок принадлежат локальному ranker, а не модели.
        draft_data["relevance"] = assessment.level
        items.append(Insight(
            **draft_data,
            id=f"insight-{uuid4().hex}",
            company_id=request.company_profile.id,
            headline=event.title,
            facts=[event.text],
            why_relevant=" ".join(reason.text for reason in draft.reasons),
            bank_view="\n\n".join(f"{s.title}: {s.text}" for s in cited_bank) or None,
            sources=[CitedSource(
                **known_sources[id_].model_dump(include=set(CitedSource.model_fields) - {"kind"}),
                kind="bank_analysis" if id_ in bank else "external_news",
            ) for id_ in draft.source_ids],
            agent_run_id=run_id,
            generated_at=generated_at,
            is_mock=selected.mode == "mock",
            relevance_score=assessment.score,
            rank=position,
            trace=InsightTrace(
                company_fields={field: company[field] for field in used_fields},
                ranking_factors=assessment.factors,
                source_ids=draft.source_ids,
                bank_source_ids=[s.id for s in cited_bank],
                steps=steps,
            ),
        ))
    return InsightResult(
        mode=selected.mode, model=selected.model_name, agent_run_id=run_id,
        generated_at=generated_at, company_id=request.company_profile.id,
        items=items, total=len(items), warnings=warnings,
        trace=RunTrace(
            attempted_mode=requested_mode, attempted_model=attempted_model,
            fallback_reason=fallback_reason, ranked_news_ids=[rank.event_id for rank in rankings],
            excluded_bank_source_ids=excluded_bank, usage=batch.usage, provider_model=batch.provider_model,
        ),
    ).model_dump(mode="json")
