"""Wybrane, prawdziwe fragmenty kodu z `src/` - do pokazania na slajdach.

Kazdy snippet to *skondensowana, czytelna* wersja kodu z realnego projektu.
Zachowane sa istotne nazwy klas/funkcji, dzieki czemu studenci moga wpisac je
w wyszukiwarke repo i znalezc pelny kontekst.

Cel: pokazac, ze prezentowany pipeline nie jest hipotetyczny - to wyciagi
z faktycznego kodu produkcyjnego (FastAPI + LangChain + Databricks + pgvector).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodeSnippet:
    title: str               # Tytul tabu / sekcji (po polsku)
    source_path: str         # Sciezka w repo, dla zaufania "to jest prawdziwe"
    description: str         # 1-2 zdania - co to robi
    why_interesting: str     # Jedno zdanie - dlaczego warto pokazac na slajdzie
    code: str                # Faktyczny kod do wyswietlenia


# ---------------------------------------------------------------------------
# 1. Protocol + MockLLM - "ten sam interfejs lokalnie i w produkcji".
# ---------------------------------------------------------------------------

SNIPPET_PROTOCOL_MOCK_LLM = CodeSnippet(
    title="Protocol + lokalny MockLLM",
    source_path="src/agents/base.py",
    description=(
        "typing.Protocol opisuje minimalny interfejs LLM (3 metody). MockLLM "
        "implementuje ten sam ksztalt, ale bez AWS - kod biegnie na laptopie "
        "bez zadnych poswiadczen."
    ),
    why_interesting=(
        "Pokazuje, ze 'duck typing' Pythona pozwala wymieniac LLM produkcyjny "
        "na fake'a w zerach linii kodu klientów."
    ),
    code='''from typing import Any, Protocol


class AgentLLM(Protocol):
    """Minimalny interfejs LLM - tylko 3 metody, nic wiecej."""

    def with_structured_output(self, *args: Any, **kwargs: Any) -> "AgentLLM": ...
    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any: ...
    def invoke(self, *args: Any, **kwargs: Any) -> Any: ...


class MockLLM:
    """Lokalny fallback gdy Bedrock niedostepny - taki sam ksztalt jak Protocol."""

    def with_structured_output(self, *args: Any, **kwargs: Any) -> "MockLLM":
        return self

    async def ainvoke(self, *args: Any, **kwargs: Any) -> dict:
        return {
            "needs_clarification": True,
            "clarification_questions": ["Which time period are you interested in?"],
            "confidence": 0.3,
        }
''',
)


# ---------------------------------------------------------------------------
# 2. ABC Credentials Provider - polimorfizm: local vs AWS Secrets Manager.
# ---------------------------------------------------------------------------

SNIPPET_CREDENTIALS_ABC = CodeSnippet(
    title="ABC: Credentials Provider (local vs AWS)",
    source_path="src/utils/database.py",
    description=(
        "Abstrakcyjna klasa bazowa definiuje 'gdzie sa hasla'. Dwie konkretne "
        "implementacje: lokalny Postgres (developer na laptopie) i AWS Secrets "
        "Manager (produkcja). Reszta kodu nie wie, ktorej uzywa."
    ),
    why_interesting=(
        "To wzorzec, dzieki ktoremu ten sam kod analityczny dziala lokalnie "
        "i w chmurze - bez `if local: ... else: ...` w 100 miejscach."
    ),
    code='''from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class DatabaseCredentials:
    username: str
    password: str
    host: str
    port: str
    database: str


class DatabaseCredentialsProvider(ABC):
    """Interfejs: 'skads wez creds'. Nikt nie wie skad, byle byly."""

    @abstractmethod
    def get_credentials(self) -> DatabaseCredentials: ...


class LocalDatabaseCredentialsProvider(DatabaseCredentialsProvider):
    """Developer na laptopie - hardcoded postgres/postgres."""

    def get_credentials(self) -> DatabaseCredentials:
        return DatabaseCredentials(
            username="postgres", password="postgres",
            host="localhost", port="5432", database="postgres",
        )


class AWSSecretsManagerDatabaseCredentialsProvider(DatabaseCredentialsProvider):
    """Produkcja - hasla z AWS Secrets Manager, z cache'em."""

    def __init__(self, secret_id: str) -> None:
        self.secret_id = secret_id
        self.secrets_manager = AWSSecretsManagerClient()

    @lru_cache
    def get_credentials(self) -> DatabaseCredentials:
        secret = self.secrets_manager.get_secret(self.secret_id)
        return DatabaseCredentials(
            username=secret.get("username", ""),
            password=secret.get("password", ""),
            host=secret.get("host", ""),
            port=str(secret.get("port", "443")),
            database=secret.get("dbname", ""),
        )
''',
)


# ---------------------------------------------------------------------------
# 3. Async + timeout + retry - prawdziwy pattern dla wolnych zapytan Databricks.
# ---------------------------------------------------------------------------

SNIPPET_ASYNC_DATABRICKS = CodeSnippet(
    title="Async + timeout + retry (Databricks)",
    source_path="src/utils/databricks_connector.py",
    description=(
        "Wykonanie zapytania na Databricks SQL Warehouse: synchroniczny driver "
        "zawiniety w `run_in_executor`, twardy timeout przez `asyncio.wait_for` "
        "i exponential backoff przy bledach przejsciowych."
    ),
    why_interesting=(
        "Jeden async/await pattern obsluguje: powolne hurtownie, timeouty, "
        "retry. To rdzenny, produkcyjny kawalek - nie tutorial z YouTube'a."
    ),
    code='''import asyncio
from databricks import sql


async def select(query: str, *, timeout_ms: int | None = None) -> list[dict]:
    """SELECT na Databricks z timeoutem klienta i retry z exponential backoff."""
    loop = asyncio.get_running_loop()
    timeout_sec = timeout_ms / 1000.0 if timeout_ms else None

    async def _run(fn, *args):
        """Sync driver -> async; jesli timeout, anuluj kursor i podnies blad."""
        fut = loop.run_in_executor(None, fn, *args)
        if timeout_sec is None:
            return await fut
        try:
            return await asyncio.wait_for(fut, timeout=timeout_sec)
        except asyncio.TimeoutError:
            cursor.cancel()
            raise TimeoutError(f"Query exceeded {timeout_ms}ms timeout")

    for attempt in range(retry_max_retries):
        try:
            with sql.connect(server_hostname=host, http_path=path,
                              access_token=token) as conn:
                with conn.cursor() as cursor:
                    await _run(cursor.execute, query)
                    cols = [d[0] for d in cursor.description]
                    rows = await _run(cursor.fetchall) or []
                    return [dict(zip(cols, row)) for row in rows]
        except Exception:
            wait = backoff_base * (backoff_factor ** attempt)
            await asyncio.sleep(wait)
    raise RuntimeError("Query failed after all retries")
''',
)


# ---------------------------------------------------------------------------
# 4. Duck typing - "jesli zachowuje sie jak DataFrame, traktuj jak DataFrame".
# ---------------------------------------------------------------------------

SNIPPET_DUCK_TYPING_DATAFRAME = CodeSnippet(
    title="Duck typing przy konwersji wynikow",
    source_path="src/utils/databricks_connector.py",
    description=(
        "Hurtownia moze zwrocic pandas DataFrame ALBO liste slownikow, "
        "zaleznie od konektora. Zamiast `isinstance(...)` sprawdzamy zachowanie: "
        "'czy umiesz .to_dict()?'. To filozofia Pythona w czystej postaci."
    ),
    why_interesting=(
        "Dla studentow biznesu: 'jesli plywa jak kaczka i krzyczy jak kaczka, "
        "to kaczka' - Python pyta o zachowanie, nie o etykietke."
    ),
    code='''def normalize_query_result(data_raw):
    """Sprowadz wynik z hurtowni do listy dict + listy kolumn."""

    # Sciezka DataFrame-like (pandas) - duck typing zamiast isinstance.
    if hasattr(data_raw, "to_dict") and hasattr(data_raw, "columns"):
        data = data_raw.to_dict("records") if not data_raw.empty else []
        columns = list(data_raw.columns) if data else []
        return data, columns

    # Sciezka list-of-dicts (np. databricks-sql-connector w starszych wersjach).
    if isinstance(data_raw, list):
        data = [row for row in data_raw if isinstance(row, dict)]
        col_set: set[str] = set()
        for row in data:
            col_set.update(row.keys())
        return data, list(col_set)

    # Wszystko inne - pusty wynik (zamiast wyjatku w sciezce krytycznej).
    return [], []
''',
)


# ---------------------------------------------------------------------------
# 5. BM25 - klasyczny algorytm IR w czystym Pythonie.
# ---------------------------------------------------------------------------

SNIPPET_BM25_PURE_PYTHON = CodeSnippet(
    title="BM25 w czystym Pythonie (hybrid retriever)",
    source_path="src/utils/hybrid_retriever.py",
    description=(
        "Klasyczny algorytm wyszukiwarki (Okapi BM25) ktory laczymy z "
        "embeddingami z pgvector. Wzor z 1995 roku - ale wciaz lapie te "
        "przypadki, ktorych embeddingi nie lapia (rzadkie tokeny, kody, ID)."
    ),
    why_interesting=(
        "Dla studentow: AI to nie tylko LLM. Klasyczne algorytmy nadal robia "
        "robote, a Python pozwala je napisac na kolanie - bez zadnych bibliotek."
    ),
    code='''import math


def bm25_score(query_tokens, doc_tokens, stats, *, k1=1.5, b=0.75):
    """Okapi BM25 - rdzen wyszukiwarek przed era embeddingow.

    `stats` zawiera: avg_dl (srednia dlugosc dokumentu),
                     df (document frequency per term),
                     n  (liczba dokumentow).
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    dl = len(doc_tokens)
    norm = 1 - b + b * (dl / stats.avg_dl) if stats.avg_dl else 1.0

    tf: dict[str, int] = {}
    for t in doc_tokens:
        tf[t] = tf.get(t, 0) + 1

    score = 0.0
    for q in query_tokens:
        n_q = stats.df.get(q, 0)
        if n_q == 0:
            continue
        idf = math.log(1 + (stats.n - n_q + 0.5) / (n_q + 0.5))
        f = tf.get(q, 0)
        if f == 0:
            continue
        score += idf * ((f * (k1 + 1)) / (f + k1 * norm))
    return score
''',
)


# ---------------------------------------------------------------------------
# 6. pgvector - vector DB w 10 liniach (LangChain + SQLAlchemy).
# ---------------------------------------------------------------------------

SNIPPET_PGVECTOR_SETUP = CodeSnippet(
    title="pgvector - vector DB w 10 liniach",
    source_path="src/utils/vector_store.py",
    description=(
        "Polaczenie do PostgreSQL z rozszerzeniem pgvector przez LangChain. "
        "SQLAlchemy daje pool polaczen i pre-ping; PGVector daje API "
        "`similarity_search_with_score`."
    ),
    why_interesting=(
        "Pokazuje, ze 'vector database' w realnym projekcie to PostgreSQL "
        "z rozszerzeniem - nie egzotyczna magia, tylko dobrze znana baza."
    ),
    code='''from langchain_postgres import PGVector
from sqlalchemy import create_engine

connection = (
    f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"
)

engine = create_engine(
    connection,
    pool_pre_ping=True,    # weryfikuj polaczenia przed uzyciem
    pool_recycle=3600,     # recykluj po godzinie (firewall friendly)
)

vector_store = PGVector(
    embeddings=create_embeddings_service(),
    collection_name="analytics_metadata",
    connection=engine,
    use_jsonb=True,        # metadane jako JSONB - szybkie filtry
)

results = vector_store.similarity_search_with_score(
    query="rentownosc klientow",
    k=5,
    filter={"type": "glossary"},
)
''',
)


# ---------------------------------------------------------------------------
# Pelna kolekcja - kolejnosc taka jak w prezentacji.
# ---------------------------------------------------------------------------

ALL_SNIPPETS: list[CodeSnippet] = [
    SNIPPET_PROTOCOL_MOCK_LLM,
    SNIPPET_CREDENTIALS_ABC,
    SNIPPET_ASYNC_DATABRICKS,
    SNIPPET_DUCK_TYPING_DATAFRAME,
    SNIPPET_BM25_PURE_PYTHON,
    SNIPPET_PGVECTOR_SETUP,
]


if __name__ == "__main__":
    for s in ALL_SNIPPETS:
        print(f"\n=== {s.title}  ({s.source_path}) ===")
        print(s.description)
        print(f"\n--- kod ---\n{s.code}")
        print(f"\nDlaczego ciekawe: {s.why_interesting}")
