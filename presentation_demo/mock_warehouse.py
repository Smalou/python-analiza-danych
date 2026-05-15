"""Mock warehouse - prezentacyjny odpowiednik hurtowni danych.

W realnym projekcie zapytania trafiają do Databricks SQL Warehouse.
Tutaj używamy pandas DataFrame jako mini-warehouse, by demo dało się
uruchomić lokalnie bez żadnych poświadczeń ani połączenia z chmurą.

Kluczowy komunikat dla studentów:
Python pozwala prototypować logikę analityczną bez pełnego środowiska
korporacyjnego - tabele, agregaty i KPI można zasymulować w kilkudziesięciu
liniach kodu.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# ---------------------------------------------------------------------------
# Dane źródłowe - symulacja tabeli `core.customer_profitability_fact`.
#
# Dataset dobrany tak, by trzy interpretacje "rentowności" dały trzech różnych
# zwycięzców:
#   - najwyższy przychód  → Customer D (2.0M, ale marża 5%)
#   - najwyższy zysk      → Customer E (200k, marża 28.6%)  ← poprawna odpowiedź
#   - najwyższa marża %   → Customer C (80%, ale tylko 40k zysku)
# ---------------------------------------------------------------------------

LAST_CLOSED_QUARTER = "2026-Q1"

_CUSTOMER_PROFITABILITY_ROWS: list[dict[str, object]] = [
    {"customer_name": "Customer A", "quarter": "2026-Q1", "net_revenue": 1_000_000, "direct_service_cost":   850_000},
    {"customer_name": "Customer B", "quarter": "2026-Q1", "net_revenue":   300_000, "direct_service_cost":   120_000},
    {"customer_name": "Customer C", "quarter": "2026-Q1", "net_revenue":    50_000, "direct_service_cost":    10_000},
    {"customer_name": "Customer D", "quarter": "2026-Q1", "net_revenue": 2_000_000, "direct_service_cost": 1_900_000},
    {"customer_name": "Customer E", "quarter": "2026-Q1", "net_revenue":   700_000, "direct_service_cost":   500_000},
    {"customer_name": "Customer F", "quarter": "2026-Q1", "net_revenue":   120_000, "direct_service_cost":    40_000},
]


def create_customer_profitability_data() -> pd.DataFrame:
    """Zwraca DataFrame z rentownością klientów (z wyliczonym zyskiem i marżą).

    Prezentacyjny odpowiednik:
        SELECT * FROM core.customer_profitability_fact
    """
    df = pd.DataFrame(_CUSTOMER_PROFITABILITY_ROWS).copy()
    df["gross_profit"] = df["net_revenue"] - df["direct_service_cost"]
    df["gross_margin_pct"] = (df["gross_profit"] / df["net_revenue"] * 100).round(1)
    return df


# ---------------------------------------------------------------------------
# Prosty "executor" - rozpoznaje wzorce zapytań z demo i zwraca DataFrame.
# W realnym systemie SQL jest wykonywany na Databricks. Tutaj pattern matching
# wystarczy - prezentacja pokazuje koncept, nie implementację parsera SQL.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryResult:
    """Wynik wykonania zapytania na mock warehouse."""

    rows: pd.DataFrame
    row_count: int
    note: str


def execute_mock_query(sql: str) -> QueryResult:
    """Wykonuje uproszczone zapytanie SQL na danych pandas.

    Funkcja nie parsuje pełnego SQL - rozpoznaje wzorce typowe dla pytań
    biznesowych z demo i zwraca odpowiednie rankingi.
    """
    sql_lower = sql.lower()
    df = create_customer_profitability_data()

    # Ranking po zysku brutto - poprawna interpretacja "rentowności" wg słownika.
    if "order by gross_profit" in sql_lower:
        return _rank_by_gross_profit(df)

    # Ranking po marży procentowej.
    if "order by gross_margin" in sql_lower:
        return _rank_by_gross_margin(df)

    # Ranking po przychodzie - typowy "domyślny" wybór bez kontekstu.
    if "order by net_revenue" in sql_lower or "order by revenue" in sql_lower:
        return _rank_by_revenue(df)

    # Domyślnie - cała tabela z limitem.
    return QueryResult(
        rows=df.head(1000),
        row_count=min(len(df), 1000),
        note="pełna tabela klientów",
    )


def _rank_by_revenue(df: pd.DataFrame) -> QueryResult:
    """Ranking klientów po przychodzie netto - interpretacja AI bez kontekstu."""
    ranked = (
        df.sort_values("net_revenue", ascending=False)
        .reset_index(drop=True)
    )
    return QueryResult(
        rows=ranked[["customer_name", "net_revenue", "gross_profit", "gross_margin_pct"]],
        row_count=len(ranked),
        note="ranking po przychodzie netto",
    )


def _rank_by_gross_profit(df: pd.DataFrame) -> QueryResult:
    """Ranking po zysku brutto - poprawna interpretacja `rentowności`."""
    ranked = (
        df.sort_values("gross_profit", ascending=False)
        .reset_index(drop=True)
    )
    return QueryResult(
        rows=ranked[["customer_name", "net_revenue", "gross_profit", "gross_margin_pct"]],
        row_count=len(ranked),
        note="ranking po zysku brutto (rentowność wg słownika firmy)",
    )


def _rank_by_gross_margin(df: pd.DataFrame) -> QueryResult:
    """Ranking po marży procentowej - bardzo mali klienci mogą zawyżać wynik."""
    ranked = (
        df.sort_values("gross_margin_pct", ascending=False)
        .reset_index(drop=True)
    )
    return QueryResult(
        rows=ranked[["customer_name", "net_revenue", "gross_profit", "gross_margin_pct"]],
        row_count=len(ranked),
        note="ranking po marży brutto %",
    )


if __name__ == "__main__":
    print(create_customer_profitability_data().to_string(index=False))
    print()
    print("--- Ranking po zysku brutto (poprawna interpretacja) ---")
    print(execute_mock_query("SELECT ... ORDER BY gross_profit DESC").rows.to_string(index=False))
