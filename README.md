# Python w erze AI — demo prezentacyjne

Uproszczona, **prezentacyjna** wersja flow agenta z projektu **self-service-ai-agent** (ok. 7 minut dla studentów finansów i rachunkowości).

**Temat:** „Python w erze AI — jak zmienia się analityka finansowa i rola specjalistów biznesowych”.

To **nie** jest produkcyjny agent. Mock: pytanie biznesowe → metadane → LLM → SQL → walidacja → hurtownia (pandas) → wynik → logi. Cała aplikacja w przeglądarce to **Streamlit w Pythonie** (interfejs + logika).

- Repozytorium: [github.com/Smalou/python-analiza-danych](https://github.com/Smalou/python-analiza-danych)
- Autorka materiałów: Sylwia Malinowska

---

## Jak uruchomić Streamlita

### Katalog roboczy

Komendy uruchamiaj z **korzenia repozytorium** — tam, gdzie leży folder `presentation_demo/`. Dzięki temu działają importy `presentation_demo.*`.

### Instalacja zależności (raz)

Wymagania: **Python 3.10+**. Zależności: `pandas`, `streamlit` (lista w `presentation_demo/requirements.txt`).

```bash
pip install -r presentation_demo/requirements.txt
```

### Start aplikacji

```bash
streamlit run presentation_demo/streamlit_app.py
```

Streamlit otworzy przeglądarkę, zwykle pod adresem **http://localhost:8501**.

Opcjonalnie inny port:

```bash
streamlit run presentation_demo/streamlit_app.py --server.port 8502
```

### Z narzędziem uv

Jeśli używasz [uv](https://docs.astral.sh/uv/), po zainstalowaniu zależności z `requirements.txt` (np. `uv pip install -r presentation_demo/requirements.txt`):

```bash
uv run streamlit run presentation_demo/streamlit_app.py
```

### Streamlit Community Cloud

W ustawieniach aplikacji ustaw **Main file path** na `presentation_demo/streamlit_app.py`, a **root** repozytorium na katalog **nadrzędny** względem `presentation_demo/` (ten sam poziom co folder `presentation_demo/`), żeby Python widział pakiet `presentation_demo`.

### W aplikacji

Nawigacja między scenami: przyciski **Wstecz** / **Dalej** u góry strony. Na wybranej scenie uruchomisz demo (np. **Uruchom asystenta AI**). Pasek boczny Streamlita jest w tej aplikacji ukryty — wszystko dzieje się w głównej treści slajdów.

---

## Wersja terminalowa (CLI)

Szybki przebieg wszystkich sekcji w konsoli (wygodne na zrzuty do slajdów):

```bash
pip install -r presentation_demo/requirements.txt
python presentation_demo/run_demo.py
```

Z uv:

```bash
uv run python presentation_demo/run_demo.py
```

---

## Struktura pakietu

Kod leży w `presentation_demo/` (layout pod monorepo).

| Plik | Rola |
|---|---|
| `presentation_demo/streamlit_app.py` | UI: sceny, demo na żywo, porównania weak/strong, fragmenty „prawdziwego” kodu. |
| `presentation_demo/run_demo.py` | Wejście CLI — wszystkie sekcje pod rząd. |
| `presentation_demo/demo_agent_flow.py` | End-to-end: prompt → mock LLM → SQL → walidacja → warehouse → insight. |
| `presentation_demo/metadata_context.py` | Słabe vs mocne metadane, wpływ na SQL. |
| `presentation_demo/sql_guardrails.py` | `validate_sql()` — blokady i ostrzeżenia. |
| `presentation_demo/mock_warehouse.py` | `execute_mock_query()` na pandas. |
| `presentation_demo/observability_demo.py` | Logi i podsumowania KPI. |
| `presentation_demo/finance_kpi_example.py` | Przykład KPI (markup vs marża). |
| `presentation_demo/real_code_snippets.py` | Fragmenty kodu z produkcyjnego `src/`. |

---

## Notatki do prezentacji

### Co pokazać w kodzie

1. **`run_agent_flow`** w `presentation_demo/demo_agent_flow.py` (~linie 108–138) — jeden pipeline w Pythonie.
2. **`naive_sql_from_weak_context()`** vs **`grounded_sql_from_strong_context()`** w `presentation_demo/metadata_context.py` — to samo pytanie, inne metadane.
3. **`validate_sql`** w `presentation_demo/sql_guardrails.py` (~80–130) — kontrola przed bazą.
4. (Bonus) Jedna zakładka ze sceny „Kod z prawdziwego projektu” w Streamlicie — np. Protocol/MockLLM, ABC credentials, async Databricks.

### Dobre zrzuty ekranu (Streamlit)

- SQL obok siebie (weak vs strong).
- Wykres „Failure rate per jakosc metadanych” (słaba vs mocna jakość kontekstu).
- `st.status` przy uruchomieniu agenta (kolejne kroki pipeline’u).

### Układ scen (8 slajdów, ~7 min)

Pytanie biznesowe ramujące całą prezentację:
**„Którzy klienci byli najbardziej rentowni w ostatnim kwartale?"**

| # | Tytuł sceny | Klucz w `SCENES` | Co pokazuje |
|---|---|---|---|
| 1 | Rola analityka się zmienia | `hook` | Hook: 300 → 1 osoba, pytanie ramujące. |
| 2 | Python łączy biznes z AI | `python_pipeline` | Pytanie + 6-krokowy pipeline + 3 trudności pod spodem. |
| 3 | **To samo pytanie. Trzy możliwe odpowiedzi.** | `ambiguity` | Ranking po przychodzie/zysku/marży — trzech różnych zwycięzców. |
| 4 | **Metadane zmieniają wszystko** | `metadata_resolution` | Definicje słownika firmy + SQL + jednoznaczna odpowiedź. |
| 5 | Demo na żywo | `live_demo` | Cały pipeline w jednym kliknięciu (`st.status`). |
| 6 | Skąd wiemy, że agentowi można ufać | `trust` | Walidacja (1 zapytanie) + pomiar (1000 zapytań). |
| 7 | Słownik, funkcja, if, pandas | `foundations_code` | Moment aha: fundament z zajęć + 4 fragmenty kodu. |
| 8 | Metadane jako warstwa kontroli | `conclusion` | Podsumowanie: bez metadanych vs z metadanymi. |

### Jedno zdanie na scenę

| Scena | Zdanie |
|---|---|
| 1. Hook | „300 osób kiedyś, 1 dziś. Czy AI zastępuje, czy wzmacnia?" |
| 2. Python pipeline | „Użytkownik pisze pytanie po polsku — Python prowadzi wszystko pomiędzy." |
| 3. Trzy odpowiedzi | „AI nie wie, co znaczy 'rentowny', dopóki organizacja tego nie zdefiniuje." |
| 4. Metadane | „Dobre metadane zamieniają niejednoznaczny prompt w kontrolowane pytanie analityczne." |
| 5. Demo | „Pięć kroków pipeline'u na żywo — patrzcie na `st.status`." |
| 6. Zaufanie | „Walidacja sprawdza jedno zapytanie. Pomiar — tysiąc. Razem = zaufanie." |
| 7. Fundamenty | „Wszystko, co właśnie zobaczyliście, jest ze słownika, funkcji, `if` i pandas." |
| 8. Podsumowanie | „Metadane to nie dokumentacja. To warstwa kontroli." |

### Klient w danych demo

Dataset (6 klientów, kwartał `2026-Q1`) jest dobrany tak, by trzy interpretacje
„rentowności" wskazywały trzech różnych zwycięzców:

| Interpretacja | Zwycięzca | Komentarz |
|---|---|---|
| Po przychodzie netto | **Customer D** (2.0M PLN) | Naiwna interpretacja — duży obrót, ale marża 5%. |
| Po zysku brutto | **Customer E** (200k PLN) | **Poprawna** — słownik firmy mówi: ranking po `gross_profit`. |
| Po marży % | **Customer C** (80%) | Mali klienci zaburzają ranking marżowy. |

---

## Mapowanie na system produkcyjny

Realny stack (`src/`): FastAPI, LangChain, Bedrock, pgvector, Databricks SQL Warehouse; pipeline: `IntentParser → MetadataAgent → SQLGenerator → SQLValidator → QueryExecutor → SummaryAgent`.

Demo w `presentation_demo/` to **te same etapy w skali 1:50**:

| Produkcja | Demo |
|---|---|
| `src/agents/sql_generator.py` | `mock_llm_generate_sql()` w `demo_agent_flow.py` |
| `src/agents/sql_validator.py` | `validate_sql()` w `sql_guardrails.py` |
| `src/utils/vector_store.py` | `MetadataContext` w `metadata_context.py` |
| `src/utils/databricks_connector.py` | `execute_mock_query()` w `mock_warehouse.py` |
| `src/utils/observability_service.py` | `compute_summary()` w `observability_demo.py` |

**Czego demo świadomie nie robi:** pełna autoryzacja i RBAC, dry-run po stronie Databricks, embeddingi i hybrid search, retry/circuit-breaker, distributed tracing, governance metadanych w stylu dbt.

**Cel:** pokazać **rolę Pythona** jako warstwy między językiem biznesu, modelem a hurtownią — produkcja dodaje bezpieczeństwo, skalę i observability wokół tej samej idei.
