"""Finance KPI - marza brutto, czyli dlaczego definicja biznesowa ma znaczenie.

Klasyczny przyklad z analityki finansowej: ten sam KPI mozna policzyc na
kilka sposobow, a tylko jeden jest poprawny ksiegowo. AI policzy to, co mu
kazemy - dlatego ekspert finansowy musi zdefiniowac formule.

Kluczowy komunikat:
AI policzy liczby. Ekspert finansowy definiuje, co znaczy "poprawnie".
"""

from __future__ import annotations

import pandas as pd

from .mock_warehouse import get_branch_profitability_data


def naive_margin(df: pd.DataFrame) -> pd.Series:
    """Naiwna, blędna definicja marzy - mylenie marzy brutto z markupem.

    markup = (revenue - cost) / cost
    Ta wartosc jest zazwyczaj WYZSZA niz prawdziwa marza brutto i wprowadza
    w blad osoby porownujace sie z benchmarkami branzowymi.
    """
    return (df["revenue"] - df["cost"]) / df["cost"] * 100


def gross_margin_percentage(df: pd.DataFrame) -> pd.Series:
    """Poprawna definicja marzy brutto.

    gross_margin_percentage = (revenue - cost) / revenue * 100

    Mianownikiem jest revenue, nie cost. Ta definicja jest spojna z RZiS,
    raportami zarzadczymi i benchmarkami branzowymi.
    Zabezpieczenie przed dzieleniem przez zero realizujemy w SQL przez NULLIF;
    tutaj wystarczy assert na danych demo.
    """
    assert (df["revenue"] > 0).all(), "revenue musi byc dodatnie"
    return (df["revenue"] - df["cost"]) / df["revenue"] * 100


def compare_margins() -> pd.DataFrame:
    """Porownuje obie definicje per oddzial - pokazuje rozjazd."""
    df = get_branch_profitability_data()
    agg = (
        df.groupby("branch", as_index=False)
        .agg(revenue=("revenue", "sum"), cost=("cost", "sum"))
    )
    agg["markup_naive_pct"] = naive_margin(agg).round(1)
    agg["gross_margin_pct_correct"] = gross_margin_percentage(agg).round(1)
    agg["delta_pp"] = (agg["markup_naive_pct"] - agg["gross_margin_pct_correct"]).round(1)
    return agg.sort_values("gross_margin_pct_correct", ascending=False).reset_index(drop=True)


def explain_difference() -> str:
    """Tekst wyjasniajacy do umieszczenia na slajdzie / w raporcie."""
    return (
        "Roznica wynika z mianownika:\n"
        "  - markup       (revenue - cost) / cost     -> zawyza wynik\n"
        "  - gross_margin (revenue - cost) / revenue  -> standard ksiegowy\n"
        "AI obliczy oba poprawnie - to ekspert finansowy decyduje, ktora liczba "
        "trafia na slajd zarzadu."
    )


if __name__ == "__main__":
    print(compare_margins().to_string(index=False))
    print()
    print(explain_difference())
