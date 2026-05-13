# Presentation demo - Python w erze AI

Uproszczona, prezentacyjna wersja flow agenta AI z projektu **self-service-ai-agent**.

Cel: 7-minutowa prezentacja dla studentów finansów i rachunkowości pod hasłem
**"Python w erze AI - jak zmienia się analityka finansowa i rola specjalistów biznesowych"**.

To demo **nie jest** produkcyjnym agentem. To slajdowa, lokalnie uruchamialna
wersja prawdziwego pipeline'u: pytanie biznesowe → metadane → LLM → SQL →
walidacja → hurtownia (mock) → wynik → logi.

Cała aplikacja prezentacyjna w przeglądarce (Streamlit) — interfejs, logika i sceny demo — jest napisana w Pythonie.

**Repozytorium:** [https://github.com/Smalou/python-analiza-danych](https://github.com/Smalou/python-analiza-danych)

**Autorka materiałów:** Sylwia Malinowska

---

## Jak uruchomić

Wymagania: Python 3.10+, `pandas`, `streamlit`.

### Wersja Streamlit (rekomendowana na prezentację)

```bash
uv run streamlit run presentation_demo/streamlit_app.py
```

**Streamlit Cloud / monorepo:** w ustawieniach aplikacji ustaw **Main file path** na `presentation_demo/streamlit_app.py` i **Root** na katalog, który **zawiera** folder `presentation_demo/` (nie wewnątrz samego pakietu). Dzięki temu `from presentation_demo…` znajdzie pakiet.

Otworzy się przeglądarka na `http://localhost:8501` z całym workflow w wersji
wizualnej (kolory brandowe, dwukolumnowe porównania, przycisk "Uruchom agenta",
wykresy, metryki). Idealne pod rzutnik.

W sidebarze możesz:
- zmienić **pytanie biznesowe** (np. z YoY produktywności na coś innego),
- przełączyć **jakość metadanych** (`mocne` ↔ `słabe`) i pokazać na żywo, jak
  zmienia się SQL i wynik walidacji,
- kliknąć **Uruchom agenta**, by zobaczyć krok-po-kroku animowany pipeline.

### Wersja terminalowa (CLI)

```bash
# Opcja A - z uv (zgodnie z konwencją projektu):
uv run python presentation_demo/run_demo.py

# Opcja B - bez uv, w czystym wirtualnym środowisku:
pip install -r presentation_demo/requirements.txt
python presentation_demo/run_demo.py
```

Cały terminal-demo trwa < 1 sekundy i wypisuje wynik z dużymi nagłówkami sekcji -
przydatne, jeśli rzutnik dostaje tylko terminal albo na zrzuty do slajdów.

---

## Co robi każdy plik

Kod pakietu leży w katalogu `presentation_demo/` (layout pod monorepo: importy `presentation_demo.*` wymagają uruchamiania z **korzenia repozytorium** albo ustawionego `PYTHONPATH` na ten katalog).

| Plik | Rola w prezentacji |
|---|---|
| `presentation_demo/streamlit_app.py` | UI prezentacyjny (na rzutnik): sceny Wstecz/Dalej, live demo agenta, side-by-side weak vs strong, sekcja z prawdziwym kodem z `src/`. |
| `presentation_demo/run_demo.py` | Wejście terminalowe; pokazuje wszystkie sekcje 1-8 w konsoli (przydatne na zrzuty do slajdów). |
| `presentation_demo/real_code_snippets.py` | 6 wybranych fragmentów z `src/` (Protocol, ABC, async Databricks, duck typing, BM25, pgvector) – współdzielone między Streamlit a terminalem. |
| `presentation_demo/demo_agent_flow.py` | End-to-end flow agenta: pytanie → prompt → mock LLM → SQL → walidacja → mock warehouse → insight + log. |
| `presentation_demo/metadata_context.py` | Słownik biznesowy, definicje KPI, opisy tabel/kolumn. Dwa warianty: **słabe** vs **mocne** metadane. |
| `presentation_demo/sql_guardrails.py` | `validate_sql()` - blokuje DROP/DELETE/UPDATE/wiele statementów, ostrzega przy `SELECT *` i braku filtra po dacie. |
| `presentation_demo/mock_warehouse.py` | Mini-hurtownia w pandas: `core.branch_productivity_fact` + `execute_mock_query()`. |
| `presentation_demo/observability_demo.py` | DataFrame z logami agenta + KPI: failure rate, średni czas, failure rate per metadata_quality. |
| `presentation_demo/finance_kpi_example.py` | Marża brutto: błędna definicja (markup) vs poprawna (gross_margin_pct). |

---

## Slajdy - co pokazać kodem

### Slajd 1 - "Python klei wszystko w jeden przepływ"
Pokaż **`run_agent_flow`** z `presentation_demo/demo_agent_flow.py` (linie ~108-138). Jeden, czytelny
pipeline z 4 kroków. Punktem prezentacji jest to, że cały AI workflow mieści się
w ~30 liniach Pythona, bo Python ma do dyspozycji LLM, walidator, pandas i logi.

Zdanie do powiedzenia:
> "Python łączy pytanie po polsku, metadane, model AI, SQL i hurtownię w jeden,
> kontrolowalny przepływ."

### Slajd 2 - "AI jest tak dobre jak metadane"
Pokaż obok siebie:
- `naive_sql_from_weak_context()` (SELECT \*, brak filtra)
- `grounded_sql_from_strong_context()` (CTE, FILTER, LIMIT, NULLIF)

z pliku `presentation_demo/metadata_context.py`.

Zdanie do powiedzenia:
> "To samo pytanie. Ten sam model. Inna jakość metadanych - inna jakość SQL.
> Definicje biznesowe są kompetencją analityka, nie modelu."

### Slajd 3 - "Python jako warstwa kontroli wokół AI"
Pokaż funkcję **`validate_sql`** z `presentation_demo/sql_guardrails.py` (linie ~80-130).

Zdanie do powiedzenia:
> "Model językowy może wygenerować DROP TABLE. Python zatrzymuje to zanim
> dotrze do bazy - to jest miejsce, gdzie kończy się magia, a zaczyna inżynieria."

### Slajd 4 (bonus) - "Co naprawdę robi się w kodzie"
Pokaż jeden z 6 fragmentów ze sceny **"Kod z prawdziwego projektu"** w aplikacji
Streamlit. Najsilniejsze 3 do wyboru:
- **`Protocol` + `MockLLM`** (`src/agents/base.py`) - duck typing pozwala podmienić
  Bedrock na lokalny fake bez zmiany kodu klienta.
- **`ABC` Credentials Provider** (`src/utils/database.py`) - ten sam interfejs
  dla local Postgres i AWS Secrets Manager. Punkt: dev = prod.
- **Async + timeout + retry** (`src/utils/databricks_connector.py`) - jak
  Python radzi sobie z wolnymi zapytaniami do hurtowni (executor + `wait_for`
  + exponential backoff).

Zdanie do powiedzenia:
> "To nie są przykłady wymyślone na slajdy. To są wyciągi z produkcyjnego
> kodu, który łączy się z Bedrock, pgvector i Databricks - tak właśnie wygląda
> Python w roli warstwy spinającej AI z biznesem."

---

## Najlepsze zrzuty na slajd

### Z wersji Streamlit (rekomendowane)

1. **Sekcja 3 - SQL side-by-side**: dwie kolumny ze SQL generowanym z weak vs
   strong metadanych. Najmocniejszy wizualnie slajd "to ten sam model i to samo
   pytanie - inne tylko metadane".
2. **Sekcja 6 - bar chart "Failure rate per jakosc metadanych"**: kolumna `weak`
   ma 80%, kolumna `strong` 0%. Idealny one-slide argument "po co eksperci
   biznesowi w erze AI".
3. **Sekcja 5 - `st.status` z animowanym Run agenta**: po kliknięciu widać kolejne
   kroki ("Buduje prompt", "Generuje SQL", "Waliduje", "Wykonuje na hurtowni").
   Dynamicznie pokazuje, że "AI" to w istocie pipeline pod kontrolą Pythona.

### Z wersji terminalowej

Najsilniejszy moment "aha" w terminalu to **Sekcja 6 (Observability)**:

```
Failure rate per jakosc metadanych:
  - strong   0.0%
  - weak     80.0%
```

Plan B: jeśli wolisz "wow" wizualne, zrób screen Sekcji 4 z zablokowanym
zapytaniem (`DROP TABLE`) - widać tam, że Python sam zatrzymał ładunek.

---

## Tytuły slajdów (propozycje)

1. *Python w erze AI - od skryptu do warstwy biznesowej*
2. *Pytanie biznesowe trafia do AI - co dzieje się pod spodem?*
3. *Metadane: różnica między "AI zgaduje" a "AI rozumie"*
4. *SQL od AI nie jest święty - walidacja po stronie Pythona*
5. *Mock warehouse - prototypowanie analityki bez chmury*
6. *Czy mój agent w ogóle działa? Observability w pandas*
7. *KPI to nie wzór - to decyzja biznesowa*
8. *Rola specjalisty biznesowego: ekspert od kontekstu, nie od składni*

---

## Jedno zdanie do powiedzenia w każdej sekcji

| Sekcja | Zdanie podczas prezentacji |
|---|---|
| 1. Pytanie biznesowe | "Użytkownik nie pisze SQL - pisze po polsku. To Python tłumaczy intencję na zapytanie." |
| 2. Kontekst metadanych | "Jakość AI = jakość metadanych. Słownik biznesowy ma większą wartość niż większy model." |
| 3. Wygenerowany SQL | "Patrzcie, jak ten sam model produkuje inny SQL, gdy dostaje definicje KPI w prompt." |
| 4. Walidacja | "Python sprawdza każde zapytanie zanim ono dotknie hurtowni - jak audytor przy fakturze." |
| 5. Wynik analizy | "Tu kończy się fragment kodu - zaczyna interpretacja biznesowa. To Wasza rola." |
| 6. Observability | "Jeśli budujemy AI, musimy też mierzyć, czy ono naprawdę działa. Tu liczy się pandas." |
| 7. KPI finansowe | "AI policzy oba wzory. Ekspert finansowy decyduje, który trafia na slajd zarządu." |

---

## Jak ten demo projekt łączy się z realnym projektem AI self-service analytics agent

Realny projekt (`src/`) to FastAPI + LangChain + AWS Bedrock + pgvector +
Databricks SQL Warehouse, z pełnym pipeline'em agentów (`src/agents/`):
`IntentParser → MetadataAgent → SQLGenerator → SQLValidator → QueryExecutor → SummaryAgent`.

Demo prezentacyjne (`presentation_demo/`) odtwarza **te same etapy w skali 1:50**:

| Realny komponent | Odpowiednik w demo |
|---|---|
| `src/agents/sql_generator.py` (Bedrock + Pydantic) | `mock_llm_generate_sql()` w `presentation_demo/demo_agent_flow.py` |
| `src/agents/sql_validator.py` (regex + dry-run) | `validate_sql()` w `presentation_demo/sql_guardrails.py` |
| `src/utils/vector_store.py` (pgvector + glossary) | `MetadataContext` w `presentation_demo/metadata_context.py` |
| `src/utils/databricks_connector.py` | `execute_mock_query()` w `presentation_demo/mock_warehouse.py` |
| `src/utils/observability_service.py` + structlog | `compute_summary()` w `presentation_demo/observability_demo.py` |

**To, czego demo świadomie NIE robi (i co robi system produkcyjny):**
- prawdziwa autoryzacja, OIDC, audit log, RBAC, row-level security,
- pełne dry-run zapytań po stronie Databricks (EXPLAIN),
- vector store z embeddingami i hybrid retrieverem,
- retry/timeout/circuit-breakers na zewnętrzne usługi,
- pełna observability (correlation id, distributed tracing, alerty),
- governance metadanych (dbt schema.yml, glossary jako kod, code review).

**Cel demo jest dydaktyczny**, nie techniczny - pokazuje **rolę Pythona** jako
warstwy orkiestracji i analityki: tłumacza między językiem biznesu, modelem AI
i hurtownią danych. Prawdziwy system robi to samo, tylko bezpieczniej, szybciej
i z większą liczbą "gwarancji jakości" wokół generatywnej części pipeline'u.
