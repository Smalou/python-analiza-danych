"""Pojedyncze wejscie do calej prezentacji.

Uruchamia kolejno wszystkie sekcje demo:
  1. Pytanie biznesowe (end-to-end flow)
  2. Kontekst metadanych (slabe vs mocne)
  3. Wygenerowany SQL (porownanie)
  4. Walidacja (guardrails)
  5. Wynik analizy (mock warehouse)
  6. Observability (logi w pandas)
  7. KPI finansowe (marza brutto)

Uruchomienie:
    uv run python presentation_demo/run_demo.py
albo:
    python presentation_demo/run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Wymus UTF-8 na stdout, by polskie litery dzialaly w terminalach Windows
# (domyslny cp1252 nie obsluguje np. 'ę', 'ą').
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except AttributeError:
    pass

# Pozwala uruchomic ten plik bezposrednio ze sciezki repo:
#     python presentation_demo/run_demo.py
# bez koniecznosci instalowania pakietu.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presentation_demo.demo_agent_flow import render_agent_run, run_agent_flow
from presentation_demo.finance_kpi_example import compare_margins, explain_difference
from presentation_demo.metadata_context import STRONG_CONTEXT, WEAK_CONTEXT
from presentation_demo.observability_demo import compute_summary, format_summary, get_agent_logs
from presentation_demo.real_code_snippets import ALL_SNIPPETS
from presentation_demo.sql_guardrails import format_validation_report, validate_sql


# ---------------------------------------------------------------------------
# Drobne helpery prezentacyjne.
# ---------------------------------------------------------------------------

BUSINESS_QUESTION = "Ktore oddzialy maja najwiekszy spadek produktywnosci rok do roku?"


def _section(title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n{title}\n{bar}")


def _subsection(title: str) -> None:
    print(f"\n--- {title} ---")


# ---------------------------------------------------------------------------
# Sekcje demo.
# ---------------------------------------------------------------------------


def section_1_business_question() -> None:
    _section("1. Pytanie biznesowe")
    print(f'Uzytkownik (np. controller finansowy) pyta:\n  "{BUSINESS_QUESTION}"')
    print(
        "\nPython musi zamienic to pytanie po polsku na poprawny SQL,\n"
        "wykonac je na hurtowni i zwrocic odpowiedz biznesowa."
    )


def section_2_metadata_context() -> None:
    _section("2. Kontekst metadanych (slabe vs mocne)")

    _subsection("SLABE metadane")
    print(WEAK_CONTEXT.to_prompt_block())

    _subsection("MOCNE metadane")
    print(STRONG_CONTEXT.to_prompt_block())


def section_3_generated_sql() -> None:
    _section("3. Wygenerowany SQL")

    _subsection("SQL przy SLABYCH metadanych")
    weak_run = run_agent_flow(BUSINESS_QUESTION, metadata=WEAK_CONTEXT)
    print(weak_run.generated_sql)

    _subsection("SQL przy MOCNYCH metadanych")
    strong_run = run_agent_flow(BUSINESS_QUESTION, metadata=STRONG_CONTEXT)
    print(strong_run.generated_sql)

    return weak_run, strong_run  # type: ignore[return-value]


def section_4_validation(weak_run, strong_run) -> None:
    _section("4. Walidacja (guardrails)")

    _subsection("Walidacja SQL ze SLABYCH metadanych")
    print(format_validation_report(weak_run.validation))

    _subsection("Walidacja SQL z MOCNYCH metadanych")
    print(format_validation_report(strong_run.validation))

    _subsection("Walidacja zlosliwego zapytania (pokaz dla slajdu)")
    malicious = "SELECT * FROM core.users; DROP TABLE core.users;"
    print(f"SQL: {malicious}")
    print(format_validation_report(validate_sql(malicious)))


def section_5_result(strong_run) -> None:
    _section("5. Wynik analizy")
    print("Przebieg agenta na pytaniu biznesowym (mocne metadane):")
    print()
    print(render_agent_run(strong_run))


def section_6_observability() -> None:
    _section("6. Observability")
    df = get_agent_logs()
    print("Probka logow agenta (12 przebiegow):")
    print(df.to_string(index=False))
    print()
    print(format_summary(compute_summary(df)))


def section_7_finance_kpi() -> None:
    _section("7. KPI finansowe - marza brutto")
    df = compare_margins()
    print(df.to_string(index=False))
    print()
    print(explain_difference())


def section_8_real_code() -> None:
    _section("8. Kod z prawdziwego projektu (src/)")
    print(
        "Te fragmenty pokazuja, ze pipeline nie jest hipotetyczny - to wyciagi"
        "\nz produkcyjnego kodu FastAPI + LangChain + pgvector + Databricks."
    )
    for idx, snippet in enumerate(ALL_SNIPPETS, start=1):
        _subsection(f"{idx}. {snippet.title}  [{snippet.source_path}]")
        print(snippet.description)
        print()
        print(snippet.code)
        print(f"-> Dlaczego ciekawe: {snippet.why_interesting}")


# ---------------------------------------------------------------------------
# Glowny entry point.
# ---------------------------------------------------------------------------


def main() -> None:
    print("Python w erze AI - demo agenta self-service analytics")
    print("(uproszczona, prezentacyjna wersja - mock data, mock LLM)")

    section_1_business_question()
    section_2_metadata_context()
    weak_run, strong_run = section_3_generated_sql()
    section_4_validation(weak_run, strong_run)
    section_5_result(strong_run)
    section_6_observability()
    section_7_finance_kpi()
    section_8_real_code()

    print("\nKoniec demo.")


if __name__ == "__main__":
    main()
