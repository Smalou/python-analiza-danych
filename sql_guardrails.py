"""SQL guardrails - dlaczego SQL wygenerowanego przez AI nie wolno wykonywac na slepo.

W realnym projekcie walidator SQL (`src/agents/sql_validator.py`) blokuje DDL/DML,
sprawdza allowlist tabel, dry-run na Databricks i nadaje validation_score.

Tutaj pokazujemy uproszczona, ale realna logike walidacji - wystarczajaco prosta,
zeby zmiescic sie na slajdzie i wystarczajaco prawdziwa, by pokazac wartosc Pythona
jako warstwy bezpieczenstwa.

Kluczowy komunikat:
Python jest warstwa kontroli wokol AI - zatrzymujemy niebezpieczne zapytania
zanim trafia do hurtowni.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ValidationIssue:
    rule: str
    severity: Severity
    message: str


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def blockers(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.HIGH]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is not Severity.HIGH]


# Operacje, ktore nigdy nie powinny pojawic sie w SQL od agenta analitycznego.
_BLOCKED_KEYWORDS: tuple[str, ...] = (
    "drop",
    "delete",
    "truncate",
    "update",
    "insert",
    "alter",
    "merge",
    "create",
    "grant",
    "revoke",
)

# Pattern dla "SELECT *" - dopuszczalne w eksploracji, problematyczne na produkcji.
_SELECT_STAR = re.compile(r"select\s+\*", re.IGNORECASE)

# Pattern szukajacy filtra po dacie/miesiacu/roku.
_HAS_DATE_FILTER = re.compile(
    r"\b(where|and)\b[^;]*\b(month|date|year|calendar_date|created_at)\b",
    re.IGNORECASE,
)

# Pattern dla wielu statementow - SQL injection via "; DROP TABLE".
_MULTI_STATEMENT = re.compile(r";\s*[a-zA-Z]")

# Pattern dla komentarzy ukrywajacych ladunek.
_COMMENT_INJECTION = re.compile(r"--|/\*")


def validate_sql(sql: str) -> ValidationResult:
    """Sprawdza, czy SQL jest bezpieczny do wykonania na hurtowni analitycznej.

    Reguly:
    1. Zablokuj DDL/DML (DROP, DELETE, UPDATE, ...) - severity HIGH.
    2. Zablokuj wiele statementow oddzielonych srednikiem - severity HIGH.
    3. Ostrzez przy SELECT * - severity MEDIUM (czesto symptom slabego promptu).
    4. Ostrzez przy braku filtra po dacie - severity MEDIUM (ryzyko full scan).
    5. Ostrzez przy obecnosci komentarzy (potencjalna inżynieria promptu) - LOW.
    """
    issues: list[ValidationIssue] = []
    normalized = sql.strip()

    # 1. Blokowane slowa kluczowe (DDL/DML).
    for keyword in _BLOCKED_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized, re.IGNORECASE):
            issues.append(
                ValidationIssue(
                    rule="blocked_operation",
                    severity=Severity.HIGH,
                    message=f"Wykryto zablokowana operacje: {keyword.upper()}",
                )
            )

    # 2. Wiele statementow.
    if _MULTI_STATEMENT.search(normalized):
        issues.append(
            ValidationIssue(
                rule="multiple_statements",
                severity=Severity.HIGH,
                message="Wykryto wiele statementow SQL (potencjalny SQL injection).",
            )
        )

    # 3. SELECT *.
    if _SELECT_STAR.search(normalized):
        issues.append(
            ValidationIssue(
                rule="select_star",
                severity=Severity.MEDIUM,
                message="SELECT * - wskaz konkretne kolumny dla czytelnosci i kosztow.",
            )
        )

    # 4. Brak filtra po dacie.
    if normalized.lower().startswith(("select", "with")) and not _HAS_DATE_FILTER.search(
        normalized
    ):
        issues.append(
            ValidationIssue(
                rule="missing_date_filter",
                severity=Severity.MEDIUM,
                message="Brak filtra po dacie - ryzyko pelnego skanu tabeli faktow.",
            )
        )

    # 5. Komentarze (LOW - tylko jako sygnal).
    if _COMMENT_INJECTION.search(normalized):
        issues.append(
            ValidationIssue(
                rule="contains_comments",
                severity=Severity.LOW,
                message="SQL zawiera komentarze - sprawdz, czy nie ukrywaja zlosliwego ladunku.",
            )
        )

    is_valid = not any(i.severity is Severity.HIGH for i in issues)
    return ValidationResult(is_valid=is_valid, issues=issues)


def format_validation_report(result: ValidationResult) -> str:
    """Formatuje wynik walidacji jako czytelny raport dla terminala/slajdu."""
    if not result.issues:
        return "OK: SQL przeszedl wszystkie reguly walidacji."

    lines = []
    status = "PRZESZLA" if result.is_valid else "ZABLOKOWANA"
    lines.append(f"Walidacja {status}. Znaleziono {len(result.issues)} uwag:")
    severity_icon = {Severity.HIGH: "[BLOK]", Severity.MEDIUM: "[OSTRZ]", Severity.LOW: "[INFO]"}
    for issue in result.issues:
        icon = severity_icon[issue.severity]
        lines.append(f"  {icon} {issue.rule}: {issue.message}")
    return "\n".join(lines)


if __name__ == "__main__":
    good_sql = (
        "SELECT branch, AVG(productivity_score) "
        "FROM core.branch_productivity_fact "
        "WHERE month >= '2024-01' GROUP BY branch LIMIT 100;"
    )
    bad_sql = "SELECT * FROM core.branch_productivity_fact; DROP TABLE core.users;"

    print("Dobre zapytanie:")
    print(format_validation_report(validate_sql(good_sql)))
    print("\nZle zapytanie:")
    print(format_validation_report(validate_sql(bad_sql)))
