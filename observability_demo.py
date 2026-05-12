"""Observability - analiza logow agenta AI w pandas.

W realnym systemie logi z agenta sa zapisywane (structlog + observability_service)
i analizowane w narzedziach typu Datadog/Grafana. Tutaj robimy minimalny
odpowiednik: DataFrame z metrykami przebiegow agenta i kilka prostych KPI.

Kluczowy komunikat:
Skoro budujemy systemy AI, musimy tez mierzyc, czy one rzeczywiscie dzialaja.
Python + pandas wystarczy, by policzyc to samodzielnie.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# ---------------------------------------------------------------------------
# Syntetyczne logi - 12 przebiegow agenta, kilka udanych, kilka padnietych.
# ---------------------------------------------------------------------------

_AGENT_LOG_ROWS: list[dict[str, object]] = [
    {"question_id": "q01", "user_question": "Top oddzialy wg przychodu",                "metadata_quality": "strong", "sql_validation_status": "ok",      "execution_status": "success", "response_time_seconds": 1.20, "rows_returned": 5},
    {"question_id": "q02", "user_question": "Spadek produktywnosci r/r",                "metadata_quality": "strong", "sql_validation_status": "ok",      "execution_status": "success", "response_time_seconds": 1.85, "rows_returned": 5},
    {"question_id": "q03", "user_question": "Pokaz wszystko z tabeli faktow",           "metadata_quality": "weak",   "sql_validation_status": "warning", "execution_status": "success", "response_time_seconds": 3.40, "rows_returned": 1000},
    {"question_id": "q04", "user_question": "Usun stare rekordy",                       "metadata_quality": "weak",   "sql_validation_status": "blocked", "execution_status": "blocked", "response_time_seconds": 0.30, "rows_returned": 0},
    {"question_id": "q05", "user_question": "Marza brutto per region",                  "metadata_quality": "strong", "sql_validation_status": "ok",      "execution_status": "success", "response_time_seconds": 1.05, "rows_returned": 3},
    {"question_id": "q06", "user_question": "Nadgodziny vs produktywnosc",              "metadata_quality": "strong", "sql_validation_status": "ok",      "execution_status": "success", "response_time_seconds": 1.50, "rows_returned": 20},
    {"question_id": "q07", "user_question": "Pokaz koszty",                             "metadata_quality": "weak",   "sql_validation_status": "warning", "execution_status": "error",   "response_time_seconds": 4.10, "rows_returned": 0},
    {"question_id": "q08", "user_question": "Pokaz koszty per miesiac w 2025",          "metadata_quality": "strong", "sql_validation_status": "ok",      "execution_status": "success", "response_time_seconds": 1.30, "rows_returned": 2},
    {"question_id": "q09", "user_question": "Drop table users",                         "metadata_quality": "weak",   "sql_validation_status": "blocked", "execution_status": "blocked", "response_time_seconds": 0.25, "rows_returned": 0},
    {"question_id": "q10", "user_question": "Region z najwyzszym przychodem",           "metadata_quality": "strong", "sql_validation_status": "ok",      "execution_status": "success", "response_time_seconds": 1.10, "rows_returned": 3},
    {"question_id": "q11", "user_question": "Top oddzialy",                             "metadata_quality": "weak",   "sql_validation_status": "warning", "execution_status": "error",   "response_time_seconds": 5.20, "rows_returned": 0},
    {"question_id": "q12", "user_question": "Marza brutto - top 3 oddzialy",            "metadata_quality": "strong", "sql_validation_status": "ok",      "execution_status": "success", "response_time_seconds": 1.40, "rows_returned": 3},
]


def get_agent_logs() -> pd.DataFrame:
    """Zwraca syntetyczny zbior logow agenta jako DataFrame."""
    return pd.DataFrame(_AGENT_LOG_ROWS)


@dataclass(frozen=True)
class ObservabilitySummary:
    total_runs: int
    successful_runs: int
    failure_rate_pct: float
    avg_response_time_seconds: float
    failure_rate_by_metadata: dict[str, float]


def compute_summary(df: pd.DataFrame) -> ObservabilitySummary:
    """Liczy podstawowe KPI obserwowalnosci."""
    total = len(df)
    successful = int((df["execution_status"] == "success").sum())
    failed = total - successful
    failure_rate = (failed / total) * 100 if total else 0.0

    # Failure rate per jakosc metadanych - kluczowy "aha-moment" prezentacji.
    df_failed = df.assign(failed=(df["execution_status"] != "success").astype(int))
    by_quality = (
        df_failed.groupby("metadata_quality")["failed"].mean().mul(100).round(1).to_dict()
    )

    return ObservabilitySummary(
        total_runs=total,
        successful_runs=successful,
        failure_rate_pct=round(failure_rate, 1),
        avg_response_time_seconds=round(df["response_time_seconds"].mean(), 2),
        failure_rate_by_metadata=by_quality,
    )


def format_summary(summary: ObservabilitySummary) -> str:
    """Formatuje podsumowanie obserwowalnosci pod slajd/terminal."""
    lines = [
        f"Liczba przebiegow:           {summary.total_runs}",
        f"Sukcesy:                     {summary.successful_runs}",
        f"Failure rate:                {summary.failure_rate_pct}%",
        f"Sredni czas odpowiedzi:      {summary.avg_response_time_seconds}s",
        "",
        "Failure rate per jakosc metadanych:",
    ]
    for quality, rate in sorted(summary.failure_rate_by_metadata.items()):
        lines.append(f"  - {quality:<8} {rate}%")
    return "\n".join(lines)


if __name__ == "__main__":
    df = get_agent_logs()
    summary = compute_summary(df)
    print(format_summary(summary))
