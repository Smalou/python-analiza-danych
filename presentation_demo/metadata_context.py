"""Metadata context - jakość metadanych a jakość SQL z LLM.

W realnym projekcie metadane przychodzą z vector store (pgvector) i obejmują:
- słownik biznesowy (glossary)
- definicje KPI
- opisy tabel i kolumn
- wzorce join'ów
- przykładowe zapytania

Tutaj pokazujemy ten sam koncept w skondensowanej, prezentacyjnej formie.

Kluczowy komunikat:
Bez metadanych model nie analizuje finansów - on zgaduje finanse.
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
        """Formatuje metadane jako blok tekstu do wstrzyknięcia w prompt."""
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
        "core.customer_profitability_fact": "tabela z danymi klientow",
    },
)


# ---------------------------------------------------------------------------
# Wariant 2 - DOBRE metadane: slownik biznesowy, KPI, opisy kolumn, przyklady.
# ---------------------------------------------------------------------------

STRONG_CONTEXT = MetadataContext(
    glossary={
        "klient": (
            "Klient fakturowany - osobny podmiot rozliczeniowy aktywny "
            "w danym kwartale (kolumna customer_name)."
        ),
        "rentowny / rentownosc": (
            "Klient o najwyzszym zysku brutto w danym okresie. "
            "Podstawowy ranking: gross_profit DESC. Marza % to miara wspierajaca."
        ),
        "ostatni kwartal": (
            "Ostatni w pelni zamkniety kwartal kalendarzowy. "
            "Wyznaczany na podstawie biezacej daty raportu."
        ),
    },
    kpi_definitions={
        "gross_profit": "net_revenue - direct_service_cost",
        "gross_margin_pct": "gross_profit / NULLIF(net_revenue, 0) * 100",
        "ranking_metric_rentownosc": "gross_profit DESC",
        "min_revenue_dla_rankingu_marzowego": (
            "100 000 PLN (klienci ponizej tego progu wykluczeni "
            "z rankingu marzy %, by uniknac mylacych wynikow)"
        ),
    },
    table_descriptions={
        "core.customer_profitability_fact": (
            "Kwartalne fakty rentownosci klientow. Ziarno: customer x quarter. "
            "Zawiera: net_revenue, direct_service_cost, gross_profit, gross_margin_pct."
        ),
    },
    column_descriptions={
        "customer_name": "Nazwa klienta fakturowanego (klucz biznesowy).",
        "quarter": "Kwartal w formacie YYYY-Q[1-4].",
        "net_revenue": "Przychod netto - bez VAT, po korektach faktur.",
        "direct_service_cost": (
            "Bezposredni koszt obslugi klienta - bez kosztow ogolnozakladowych."
        ),
        "gross_profit": "Zysk brutto = net_revenue - direct_service_cost.",
        "gross_margin_pct": "Marza brutto % = gross_profit / net_revenue * 100.",
    },
    example_queries=[
        (
            "-- Top 5 klientow wg zysku brutto w ostatnim zamknietym kwartale\n"
            "SELECT customer_name, net_revenue, gross_profit, gross_margin_pct\n"
            "FROM core.customer_profitability_fact\n"
            "WHERE quarter = '2026-Q1'\n"
            "ORDER BY gross_profit DESC\n"
            "LIMIT 5;"
        ),
    ],
)


def naive_sql_from_weak_context(question: str) -> str:
    """SQL, jaki LLM moglby wygenerowac przy slabym kontekscie.

    Bez slownika "rentownosc" → AI zgaduje najprostsza interpretacje:
    "rentowny" = "ma duzo pieniedzy" = "wysoki przychod".
    Pomija filtr kwartalu i ranking po zysku.
    """
    _ = question
    return (
        "SELECT customer_name, net_revenue\n"
        "FROM core.customer_profitability_fact\n"
        "ORDER BY net_revenue DESC\n"
        "LIMIT 5;"
    )


def grounded_sql_from_strong_context(question: str) -> str:
    """SQL przy dobrym kontekscie - ranking po zysku brutto, ostatni kwartal."""
    _ = question
    return (
        "SELECT customer_name,\n"
        "       net_revenue,\n"
        "       gross_profit,\n"
        "       gross_margin_pct\n"
        "FROM core.customer_profitability_fact\n"
        "WHERE quarter = '2026-Q1'\n"
        "ORDER BY gross_profit DESC\n"
        "LIMIT 5;"
    )


if __name__ == "__main__":
    print("=== Slaby kontekst ===")
    print(WEAK_CONTEXT.to_prompt_block())
    print("\n=== Mocny kontekst ===")
    print(STRONG_CONTEXT.to_prompt_block())
