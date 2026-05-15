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
# Dane źródłowe - symulacja tabeli `core.branch_productivity_fact`
# ---------------------------------------------------------------------------

_BRANCH_PRODUCTIVITY_ROWS: list[dict[str, object]] = [
    # Branch A - region North - lekki spadek r/r
    {"branch": "A", "region": "North", "month": "2024-01", "revenue": 120_000, "cost": 80_000, "productivity_score": 0.82, "overtime_hours": 110},
    {"branch": "A", "region": "North", "month": "2024-02", "revenue": 118_000, "cost": 82_000, "productivity_score": 0.80, "overtime_hours": 130},
    {"branch": "A", "region": "North", "month": "2025-01", "revenue": 115_000, "cost": 85_000, "productivity_score": 0.74, "overtime_hours": 180},
    {"branch": "A", "region": "North", "month": "2025-02", "revenue": 112_000, "cost": 87_000, "productivity_score": 0.71, "overtime_hours": 210},

    # Branch B - region South - duzy spadek marzy brutto r/r (rosnacy koszt)
    {"branch": "B", "region": "South", "month": "2024-01", "revenue": 150_000, "cost": 95_000, "productivity_score": 0.88, "overtime_hours": 80},
    {"branch": "B", "region": "South", "month": "2024-02", "revenue": 148_000, "cost": 96_000, "productivity_score": 0.86, "overtime_hours": 95},
    {"branch": "B", "region": "South", "month": "2025-01", "revenue": 140_000, "cost": 105_000, "productivity_score": 0.65, "overtime_hours": 260},
    {"branch": "B", "region": "South", "month": "2025-02", "revenue": 135_000, "cost": 110_000, "productivity_score": 0.60, "overtime_hours": 290},

    # Branch C - region West - stabilny
    {"branch": "C", "region": "West",  "month": "2024-01", "revenue": 200_000, "cost": 130_000, "productivity_score": 0.79, "overtime_hours": 120},
    {"branch": "C", "region": "West",  "month": "2024-02", "revenue": 205_000, "cost": 132_000, "productivity_score": 0.80, "overtime_hours": 115},
    {"branch": "C", "region": "West",  "month": "2025-01", "revenue": 210_000, "cost": 134_000, "productivity_score": 0.81, "overtime_hours": 110},
    {"branch": "C", "region": "West",  "month": "2025-02", "revenue": 215_000, "cost": 136_000, "productivity_score": 0.82, "overtime_hours": 105},

    # Branch D - region North - lekka poprawa
    {"branch": "D", "region": "North", "month": "2024-01", "revenue": 90_000,  "cost": 70_000, "productivity_score": 0.70, "overtime_hours": 150},
    {"branch": "D", "region": "North", "month": "2024-02", "revenue": 92_000,  "cost": 71_000, "productivity_score": 0.72, "overtime_hours": 140},
    {"branch": "D", "region": "North", "month": "2025-01", "revenue": 95_000,  "cost": 70_000, "productivity_score": 0.78, "overtime_hours": 120},
    {"branch": "D", "region": "North", "month": "2025-02", "revenue": 97_000,  "cost": 69_500, "productivity_score": 0.80, "overtime_hours": 115},

    # Branch E - region South - umiarkowany spadek marzy brutto r/r
    {"branch": "E", "region": "South", "month": "2024-01", "revenue": 130_000, "cost": 88_000, "productivity_score": 0.84, "overtime_hours": 100},
    {"branch": "E", "region": "South", "month": "2024-02", "revenue": 132_000, "cost": 89_000, "productivity_score": 0.83, "overtime_hours": 105},
    {"branch": "E", "region": "South", "month": "2025-01", "revenue": 128_000, "cost": 95_000, "productivity_score": 0.73, "overtime_hours": 170},
    {"branch": "E", "region": "South", "month": "2025-02", "revenue": 126_000, "cost": 97_000, "productivity_score": 0.70, "overtime_hours": 185},
]


def get_branch_productivity_data() -> pd.DataFrame:
    """Zwraca surowy DataFrame z faktami produktywnosci oddzialow.

    To prezentacyjny odpowiednik zapytania:
        SELECT * FROM core.branch_productivity_fact
    """
    df = pd.DataFrame(_BRANCH_PRODUCTIVITY_ROWS)
    df["year"] = df["month"].str.slice(0, 4).astype(int)
    return df


# ---------------------------------------------------------------------------
# Prosty "executor" - rozpoznaje wzorce zapytan z demo i zwraca DataFrame.
# W realnym systemie SQL jest wykonywany na Databricks. Tutaj pattern matching
# wystarczy - prezentacja pokazuje koncept, nie implementacje parsera SQL.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryResult:
    """Wynik wykonania zapytania na mock warehouse."""

    rows: pd.DataFrame
    row_count: int
    note: str


def execute_mock_query(sql: str) -> QueryResult:
    """Wykonuje uproszczone zapytanie SQL na danych pandas.

    Funkcja nie parsuje pelnego SQL - zamiast tego rozpoznaje wzorce
    typowe dla pytan biznesowych z demo i zwraca odpowiednie agregaty.
    """
    sql_lower = sql.lower()
    df = get_branch_productivity_data()

    if "year_over_year" in sql_lower or "yoy" in sql_lower or "spadek" in sql_lower:
        return _branch_yoy_drop(df)

    if "group by branch" in sql_lower and "revenue" in sql_lower:
        agg = (
            df.groupby("branch", as_index=False)
            .agg(total_revenue=("revenue", "sum"), total_cost=("cost", "sum"))
            .sort_values("total_revenue", ascending=False)
        )
        return QueryResult(rows=agg, row_count=len(agg), note="agregacja po oddziale")

    if "group by region" in sql_lower:
        agg = (
            df.groupby("region", as_index=False)
            .agg(total_revenue=("revenue", "sum"), total_cost=("cost", "sum"))
            .sort_values("total_revenue", ascending=False)
        )
        return QueryResult(rows=agg, row_count=len(agg), note="agregacja po regionie")

    # Domyslnie - zwroc wszystko (z limitem)
    return QueryResult(rows=df.head(1000), row_count=min(len(df), 1000), note="pelna tabela")


def _branch_yoy_drop(df: pd.DataFrame) -> QueryResult:
    """Liczy zmiane marzy brutto 2025 vs 2024 per oddzial.

    Marza brutto = (revenue - cost) / revenue * 100 (poprawna definicja ksiegowa).
    YoY wyrazone w punktach procentowych (pp) - klasyczna miara dla marz.
    """
    yearly = (
        df.groupby(["branch", "year"], as_index=False)
        .agg(revenue=("revenue", "sum"), cost=("cost", "sum"))
    )
    yearly["gross_margin_pct"] = (
        (yearly["revenue"] - yearly["cost"]) / yearly["revenue"] * 100
    )
    pivoted = (
        yearly.pivot(index="branch", columns="year", values="gross_margin_pct")
        .reset_index()
    )
    pivoted["yoy_change_pp"] = (pivoted[2025] - pivoted[2024]).round(2)
    pivoted = pivoted.rename(
        columns={2024: "gross_margin_2024_pct", 2025: "gross_margin_2025_pct"}
    )
    pivoted["gross_margin_2024_pct"] = pivoted["gross_margin_2024_pct"].round(2)
    pivoted["gross_margin_2025_pct"] = pivoted["gross_margin_2025_pct"].round(2)
    pivoted = pivoted.sort_values("yoy_change_pp").reset_index(drop=True)
    return QueryResult(
        rows=pivoted[
            ["branch", "gross_margin_2024_pct", "gross_margin_2025_pct", "yoy_change_pp"]
        ],
        row_count=len(pivoted),
        note="YoY marzy brutto per oddzial",
    )


if __name__ == "__main__":
    print(get_branch_productivity_data().head())
    print()
    print(execute_mock_query("SELECT branch, yoy ...").rows)
