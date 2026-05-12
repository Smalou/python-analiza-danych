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
        "produktywnosc": (
            "Wskaznik 0..1 obliczany jako stosunek zrealizowanych zadan "
            "do planowanych. Wyzszy = lepiej."
        ),
        "spadek r/r (YoY)": (
            "Zmiana procentowa miedzy biezacym a poprzednim rokiem dla tej "
            "samej miary (current - previous) / previous * 100."
        ),
        "oddzial": "Jednostka organizacyjna - kolumna `branch` w tabelach faktow.",
    },
    kpi_definitions={
        "gross_margin_pct": "(revenue - cost) / NULLIF(revenue, 0) * 100",
        "productivity_yoy_change_pct": (
            "(AVG(productivity_score) FILTER (year = 2025) "
            "- AVG(productivity_score) FILTER (year = 2024)) "
            "/ AVG(productivity_score) FILTER (year = 2024) * 100"
        ),
    },
    table_descriptions={
        "core.branch_productivity_fact": (
            "Miesieczne fakty produktywnosci oddzialow. Ziarno: branch x month. "
            "Aktualizowana 5. dnia roboczego miesiaca."
        ),
    },
    column_descriptions={
        "branch": "Kod oddzialu (varchar). Klucz biznesowy.",
        "region": "Region geograficzny (North/South/West).",
        "month": "Miesiac w formacie YYYY-MM.",
        "revenue": "Przychod w PLN, bez VAT.",
        "cost": "Koszt calkowity oddzialu w PLN.",
        "productivity_score": "Produktywnosc 0..1 (patrz slownik).",
        "overtime_hours": "Suma godzin nadliczbowych w miesiacu.",
    },
    example_queries=[
        (
            "-- Top 3 oddzialy ze spadkiem produktywnosci r/r\n"
            "WITH yearly AS (\n"
            "  SELECT branch, EXTRACT(YEAR FROM TO_DATE(month, 'yyyy-MM')) AS y,\n"
            "         AVG(productivity_score) AS p\n"
            "  FROM core.branch_productivity_fact\n"
            "  GROUP BY 1, 2\n"
            ")\n"
            "SELECT branch,\n"
            "       MAX(p) FILTER (WHERE y = 2024) AS p_2024,\n"
            "       MAX(p) FILTER (WHERE y = 2025) AS p_2025,\n"
            "       (MAX(p) FILTER (WHERE y = 2025)\n"
            "        / NULLIF(MAX(p) FILTER (WHERE y = 2024), 0) - 1) * 100\n"
            "         AS yoy_change_pct\n"
            "FROM yearly\n"
            "GROUP BY branch\n"
            "ORDER BY yoy_change_pct ASC\n"
            "LIMIT 3;"
        ),
    ],
)


def naive_sql_from_weak_context(question: str) -> str:
    """Symulacja SQL, ktory LLM moglby wygenerowac przy slabym kontekscie.

    Pokazuje typowe braki: brak filtra czasu, niejasna definicja "spadku",
    brak agregacji, SELECT * - czyli zapytanie "niby dziala" ale do niczego
    sie nie nadaje w analityce finansowej.
    """
    _ = question
    return (
        "SELECT *\n"
        "FROM core.branch_productivity_fact\n"
        "ORDER BY productivity_score ASC;"
    )


def grounded_sql_from_strong_context(question: str) -> str:
    """Symulacja SQL przy dobrym kontekscie - poprawnie liczy YoY i ogranicza wynik."""
    _ = question
    return (
        "WITH yearly AS (\n"
        "  SELECT branch,\n"
        "         EXTRACT(YEAR FROM TO_DATE(month, 'yyyy-MM')) AS year_over_year,\n"
        "         AVG(productivity_score) AS productivity_avg\n"
        "  FROM core.branch_productivity_fact\n"
        "  WHERE month >= '2024-01'\n"
        "  GROUP BY 1, 2\n"
        ")\n"
        "SELECT branch,\n"
        "       MAX(productivity_avg) FILTER (WHERE year_over_year = 2024) "
        "AS productivity_2024,\n"
        "       MAX(productivity_avg) FILTER (WHERE year_over_year = 2025) "
        "AS productivity_2025,\n"
        "       (MAX(productivity_avg) FILTER (WHERE year_over_year = 2025)\n"
        "        / NULLIF(MAX(productivity_avg) FILTER (WHERE year_over_year = 2024), 0)\n"
        "        - 1) * 100 AS yoy_change_pct\n"
        "FROM yearly\n"
        "GROUP BY branch\n"
        "ORDER BY yoy_change_pct ASC\n"
        "LIMIT 5;"
    )


if __name__ == "__main__":
    print("=== Slaby kontekst ===")
    print(WEAK_CONTEXT.to_prompt_block())
    print("\n=== Mocny kontekst ===")
    print(STRONG_CONTEXT.to_prompt_block())
