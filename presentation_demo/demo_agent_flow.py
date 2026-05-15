"""End-to-end flow agenta AI w skondensowanej, prezentacyjnej formie.

Realny pipeline (src/api/application/, src/agents/):
    pytanie -> intent_parser -> metadata_agent -> sql_generator
            -> sql_validator -> query_executor -> summary_agent -> observability

Tutaj te same etapy odtwarzamy w jednym pliku, bez frameworkow, bez chmury,
z mockowanym LLM. Cel: pokazac, ze Python jest "klejem" laczacym jezyk biznesu,
metadane, AI, SQL i analitykę.

Kluczowy komunikat:
Python lączy pytanie biznesowe, metadane, LLM, SQL i wynik w jeden, kontrolowany przeplyw.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from .metadata_context import (
    MetadataContext,
    STRONG_CONTEXT,
    grounded_sql_from_strong_context,
    naive_sql_from_weak_context,
)
from .mock_warehouse import QueryResult, execute_mock_query
from .sql_guardrails import ValidationResult, format_validation_report, validate_sql


# ---------------------------------------------------------------------------
# Stan agenta - prosty odpowiednik AgentState z LangGraph w realnym projekcie.
# ---------------------------------------------------------------------------


@dataclass
class AgentRun:
    question_id: str
    user_question: str
    metadata: MetadataContext
    prompt: str = ""
    generated_sql: str = ""
    validation: ValidationResult | None = None
    query_result: QueryResult | None = None
    insight: str = ""
    log: list[str] = field(default_factory=list)
    response_time_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Mock LLM - deterministyczny "model", ktory wybiera SQL na podstawie jakosci
# metadanych. W realnym kodzie tutaj wywoływany jest Bedrock + Pydantic
# structured output (patrz src/agents/sql_generator.py).
# ---------------------------------------------------------------------------


def mock_llm_generate_sql(question: str, context: MetadataContext) -> str:
    """Mockowany LLM - zwraca slabszy lub mocniejszy SQL zaleznie od metadanych.

    Dydaktycznie pokazuje, że jakosc outputu LLM zalezy od kontekstu, nie od magii.
    """
    has_kpi = bool(context.kpi_definitions)
    has_glossary = bool(context.glossary)
    if has_kpi and has_glossary:
        return grounded_sql_from_strong_context(question)
    return naive_sql_from_weak_context(question)


def build_prompt(question: str, context: MetadataContext) -> str:
    """Sklada prompt z pytania uzytkownika i kontekstu metadanych."""
    return (
        "# Rola\n"
        "Jestes agentem analitycznym piszacym Databricks SQL.\n"
        "Generuj wylacznie zapytania SELECT/WITH, dodawaj LIMIT, filtruj po dacie.\n\n"
        "# Kontekst metadanych\n"
        f"{context.to_prompt_block()}\n\n"
        "# Pytanie uzytkownika\n"
        f"{question}\n"
    )


# ---------------------------------------------------------------------------
# Streszczenie wyniku - prezentacyjny odpowiednik SummaryAgent.
# ---------------------------------------------------------------------------


def summarize_result(result: QueryResult) -> str:
    """Tworzy krotka odpowiedz biznesowa z DataFrame zwroconego przez warehouse."""
    df = result.rows
    if df.empty:
        return "Brak danych spelniajacych kryteria pytania."

    if "gross_profit" in df.columns and "customer_name" in df.columns:
        top = df.iloc[0]
        return (
            f"Najbardziej rentowny klient w ostatnim kwartale: '{top['customer_name']}' "
            f"(zysk brutto {top['gross_profit']:,.0f} PLN, "
            f"marza {top['gross_margin_pct']:.1f}%)."
        )

    return f"Zwrocono {result.row_count} wierszy ({result.note})."


# ---------------------------------------------------------------------------
# Glowna funkcja orchestrujaca - jeden, czytelny pipeline.
# ---------------------------------------------------------------------------


def run_agent_flow(
    question: str,
    metadata: MetadataContext = STRONG_CONTEXT,
    llm: Callable[[str, MetadataContext], str] = mock_llm_generate_sql,
) -> AgentRun:
    """Uruchamia caly przeplyw agenta na jednym pytaniu biznesowym."""
    started = time.perf_counter()
    run = AgentRun(
        question_id=uuid.uuid4().hex[:8],
        user_question=question,
        metadata=metadata,
    )

    # 1. Zbuduj prompt z pytania + metadanych.
    run.prompt = build_prompt(question, metadata)
    run.log.append("prompt_built")

    # 2. Wygeneruj SQL (mockowany LLM).
    run.generated_sql = llm(question, metadata)
    run.log.append("sql_generated")

    # 3. Walidacja SQL (guardrails).
    run.validation = validate_sql(run.generated_sql)
    run.log.append(
        "sql_validated_ok" if run.validation.is_valid else "sql_validated_blocked"
    )

    # 4. Wykonanie na mock warehouse (tylko gdy walidacja zezwala).
    if run.validation.is_valid:
        run.query_result = execute_mock_query(run.generated_sql)
        run.log.append(f"executed_rows={run.query_result.row_count}")
        run.insight = summarize_result(run.query_result)
        run.log.append("insight_built")
    else:
        run.insight = "Zapytanie zablokowane przez walidator - nie zostalo wykonane."
        run.log.append("execution_skipped")

    run.response_time_seconds = round(time.perf_counter() - started, 4)
    return run


def render_agent_run(run: AgentRun) -> str:
    """Formatuje przebieg agenta jako czytelny tekst pod slajd/terminal."""
    blocks = [
        f"question_id: {run.question_id}",
        f"czas: {run.response_time_seconds}s",
        f"log: {run.log}",
        "",
        "--- SQL ---",
        run.generated_sql,
        "",
        "--- Walidacja ---",
        format_validation_report(run.validation) if run.validation else "(brak)",
        "",
        "--- Insight ---",
        run.insight,
    ]
    return "\n".join(blocks)


if __name__ == "__main__":
    question_pl = (
        "Ktorzy klienci byli najbardziej rentowni w ostatnim kwartale?"
    )
    run = run_agent_flow(question_pl)
    print(render_agent_run(run))
