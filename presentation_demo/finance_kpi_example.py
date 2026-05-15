"""Customer profitability - trzy interpretacje "najbardziej rentownego klienta".

Klasyczny przyklad niejednoznacznosci w analityce finansowej: pytanie "ktorzy
klienci byli najbardziej rentowni" mozna zinterpretowac na trzy rozne sposoby,
i kazda z interpretacji da innego zwyciezce.

Kluczowy komunikat:
AI nie wie, co znaczy "rentowny", dopoki organizacja tego nie zdefiniuje.
"""

from __future__ import annotations

import pandas as pd

from .mock_warehouse import create_customer_profitability_data


_RANKING_COLUMNS = ["customer_name", "net_revenue", "gross_profit", "gross_margin_pct"]


def top_by_revenue(df: pd.DataFrame | None = None, n: int = 3) -> pd.DataFrame:
    """Top N klientow wg przychodu netto - typowa "naiwna" interpretacja AI."""
    df = create_customer_profitability_data() if df is None else df
    return (
        df.sort_values("net_revenue", ascending=False)
        .head(n)
        .reset_index(drop=True)[_RANKING_COLUMNS]
    )


def top_by_gross_profit(df: pd.DataFrame | None = None, n: int = 3) -> pd.DataFrame:
    """Top N klientow wg zysku brutto - POPRAWNA interpretacja wg slownika firmy."""
    df = create_customer_profitability_data() if df is None else df
    return (
        df.sort_values("gross_profit", ascending=False)
        .head(n)
        .reset_index(drop=True)[_RANKING_COLUMNS]
    )


def top_by_gross_margin(df: pd.DataFrame | None = None, n: int = 3) -> pd.DataFrame:
    """Top N klientow wg marzy procentowej - mali klienci moga zaburzac ranking."""
    df = create_customer_profitability_data() if df is None else df
    return (
        df.sort_values("gross_margin_pct", ascending=False)
        .head(n)
        .reset_index(drop=True)[_RANKING_COLUMNS]
    )


def compare_three_interpretations() -> dict[str, pd.DataFrame]:
    """Zwraca slownik z trzema rankingami - rdzen sceny "trzy odpowiedzi"."""
    df = create_customer_profitability_data()
    return {
        "po_przychodzie": top_by_revenue(df),
        "po_zysku_brutto": top_by_gross_profit(df),
        "po_marzy_pct": top_by_gross_margin(df),
    }


def explain_difference() -> str:
    """Tekst pod slajd/terminal - dlaczego trzy interpretacje daja rozne wyniki."""
    return (
        "Trzy interpretacje 'rentownego' daja trzech innych zwyciezcow:\n"
        "  - wg przychodu      -> klient z najwiekszym obrotem (czesto niska marza)\n"
        "  - wg zysku brutto   -> klient zostawiajacy najwiecej zysku w PLN  [POPRAWNE]\n"
        "  - wg marzy %        -> klient z najwyzsza marza % (czesto bardzo maly)\n"
        "Slownik firmy: 'rentowny' = ranking po gross_profit."
    )


if __name__ == "__main__":
    rankings = compare_three_interpretations()
    for label, df in rankings.items():
        print(f"\n--- Top wg {label} ---")
        print(df.to_string(index=False))
    print()
    print(explain_difference())
