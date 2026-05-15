"""Metadata context - jakosc metadanych a jakosc SQL z LLM.

W realnym projekcie metadane przychodza z vector store (pgvector) i obejmuja:
- slownik biznesowy (glossary)
- definicje KPI
- opisy tabel i kolumn
- wzorce join'ow
- przykladowe zapytania

Tutaj pokazujemy ten sam koncept w skondensowanej, prezentacyjnej formie.

Kluczowy komunikat:
Jakosc odpowiedzi LLM zalezy bardziej od jakosci metadanych niz od mocy modelu.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetadataContext:
    """Kontekst metadanych przekazywany do LLM jako prompt context."""

    glossary: dict[str, str] = field(default_factory=dict)
    kpi_definitions: dict[str, str] = field(default_factory=dict)
    table_descriptions: dict[str, str] = field(default_factory=dict)
    column_descriptions: dict[str, str] = field(default_factory=dict)
    example_queries: list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Formatuje metadane jako blok tekstu do wstrzykniecia w prompt."""
        parts: list[str] = []
        if self.glossary:
            parts.append("# Slownik biznesowy")
            for term, meaning in self.glossary.items():
                parts.append(f"- {term}: {meaning}")
        if self.kpi_definitions:
            parts.append("\n# Definicje KPI")
            for kpi, formula in self.kpi_definitions.items():
                parts.append(f"- {kpi} = {formula}")
        if self.table_descriptions:
            parts.append("\n# Tabele")
            for table, desc in self.table_descriptions.items():
                parts.append(f"- {table}: {desc}")
        if self.column_descriptions:
            parts.append("\n# Kolumny")
            for col, desc in self.column_descriptions.items():
                parts.append(f"- {col}: {desc}")
        if self.example_queries:
            parts.append("\n# Przykladowe zapytania")
            for q in self.example_queries:
                parts.append(f"- {q}")
        return "\n".join(parts) if parts else "(brak metadanych)"


# ---------------------------------------------------------------------------
# Wariant 1 - SLABE metadane: tylko nazwy tabel, zero definicji biznesowych.
# ---------------------------------------------------------------------------

WEAK_CONTEXT = MetadataContext(
    table_descriptions={
        "core.branch_productivity_fact": "tabela z danymi oddzialow",
    },
)


# ---------------------------------------------------------------------------
# Wariant 2 - DOBRE metadane: slownik, KPI, opisy kolumn, przyklady.
# ---------------------------------------------------------------------------

STRONG_CONTEXT = MetadataContext(
    glossary={
        "wynik": (
            "Wynik finansowy oddzialu - w naszej firmie rozumiany jako marza brutto "
            "(gross margin). Patrz definicje KPI ponizej."
        ),
        "spadek r/r (YoY)": (
            "Zmiana wartosci miedzy biezacym a poprzednim rokiem dla tej samej miary. "
            "Dla marzy wyrazana w punktach procentowych (pp)."
        ),
        "oddzial": "Jednostka organizacyjna - kolumna `branch` w tabelach faktow.",
    },
    kpi_definitions={
        "gross_margin_pct": "(revenue - cost) / NULLIF(revenue, 0) * 100",
        "gross_margin_yoy_change_pp": (
            "gross_margin_pct(year=2025) - gross_margin_pct(year=2024) "
            "(roznica w punktach procentowych)"
        ),
    },
    table_descriptions={
        "core.branch_productivity_fact": (
            "Miesieczne fakty oddzialow: przychod, koszt, produktywnosc operacyjna, "
            "nadgodziny. Ziarno: branch x month. Aktualizowana 5. dnia roboczego miesiaca."
        ),
    },
    column_descriptions={
        "branch": "Kod oddzialu (varchar). Klucz biznesowy.",
        "region": "Region geograficzny (North/South/West).",
        "month": "Miesiac w formacie YYYY-MM.",
        "revenue": "Przychod w PLN, bez VAT.",
        "cost": "Koszt calkowity oddzialu w PLN.",
        "productivity_score": "Operacyjna miara produktywnosci 0..1 (nie finansowa).",
        "overtime_hours": "Suma godzin nadliczbowych w miesiacu.",
    },
    example_queries=[
        (
            "-- Top 3 oddzialy ze spadkiem marzy brutto r/r\n"
            "WITH yearly AS (\n"
            "  SELECT branch, EXTRACT(YEAR FROM TO_DATE(month, 'yyyy-MM')) AS y,\n"
            "         SUM(revenue) AS rev, SUM(cost) AS cost\n"
            "  FROM core.branch_productivity_fact\n"
            "  GROUP BY 1, 2\n"
            ")\n"
            "SELECT branch,\n"
            "       MAX((rev - cost) / NULLIF(rev, 0) * 100) FILTER (WHERE y = 2024) AS gm_2024,\n"
            "       MAX((rev - cost) / NULLIF(rev, 0) * 100) FILTER (WHERE y = 2025) AS gm_2025,\n"
            "       (MAX((rev - cost) / NULLIF(rev, 0) * 100) FILTER (WHERE y = 2025)\n"
            "        - MAX((rev - cost) / NULLIF(rev, 0) * 100) FILTER (WHERE y = 2024))\n"
            "       AS yoy_change_pp\n"
            "FROM yearly\n"
            "GROUP BY branch\n"
            "ORDER BY yoy_change_pp ASC\n"
            "LIMIT 3;"
        ),
    ],
)


def naive_sql_from_weak_context(question: str) -> str:
    """Symulacja SQL, ktory LLM moglby wygenerowac przy slabym kontekscie.

    Pokazuje typowe braki: brak filtra czasu, brak definicji "wyniku" (AI zgaduje
    ze chodzi o revenue), brak agregacji, SELECT * - czyli zapytanie "niby dziala"
    ale do niczego sie nie nadaje w analityce finansowej.
    """
    _ = question
    return (
        "SELECT *\n"
        "FROM core.branch_productivity_fact\n"
        "ORDER BY revenue ASC;"
    )


def grounded_sql_from_strong_context(question: str) -> str:
    """Symulacja SQL przy dobrym kontekscie - poprawnie liczy YoY marzy brutto."""
    _ = question
    return (
        "WITH yearly AS (\n"
        "  SELECT branch,\n"
        "         EXTRACT(YEAR FROM TO_DATE(month, 'yyyy-MM')) AS year_over_year,\n"
        "         SUM(revenue) AS revenue_sum,\n"
        "         SUM(cost) AS cost_sum\n"
        "  FROM core.branch_productivity_fact\n"
        "  WHERE month >= '2024-01'\n"
        "  GROUP BY 1, 2\n"
        ")\n"
        "SELECT branch,\n"
        "       MAX((revenue_sum - cost_sum) / NULLIF(revenue_sum, 0) * 100)\n"
        "         FILTER (WHERE year_over_year = 2024) AS gross_margin_2024_pct,\n"
        "       MAX((revenue_sum - cost_sum) / NULLIF(revenue_sum, 0) * 100)\n"
        "         FILTER (WHERE year_over_year = 2025) AS gross_margin_2025_pct,\n"
        "       (MAX((revenue_sum - cost_sum) / NULLIF(revenue_sum, 0) * 100)\n"
        "          FILTER (WHERE year_over_year = 2025)\n"
        "        - MAX((revenue_sum - cost_sum) / NULLIF(revenue_sum, 0) * 100)\n"
        "          FILTER (WHERE year_over_year = 2024))\n"
        "       AS yoy_change_pp\n"
        "FROM yearly\n"
        "GROUP BY branch\n"
        "ORDER BY yoy_change_pp ASC\n"
        "LIMIT 5;"
    )


if __name__ == "__main__":
    print("=== Slaby kontekst ===")
    print(WEAK_CONTEXT.to_prompt_block())
    print("\n=== Mocny kontekst ===")
    print(STRONG_CONTEXT.to_prompt_block())
