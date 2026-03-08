v---
title: "Lab 2: Nawigacja po API — stronicowanie, pipeline, retry"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Automatyczne przechodzenie po wielu stronach wyników API (stronicowanie),
* Budowanie pipeline'u: wyszukiwanie → metadane → pobranie pliku,
* Pobieranie plików binarnych (CSV, XLSX) z adresów uzyskanych przez API,
* Obsługa błędów przejściowych — wzorzec retry z backoffem,
* Pisanie funkcji wielokrotnego użytku (reużywalny kod klienta API).

Narzędzia: Python (`requests`, `pathlib`, `json`, `time`).

Kontynuujemy pracę z API dane.gov.pl — korzystamy z tych samych wzorców co w Lab 1 (`save_response`, stała `API`, katalog wyjściowy).

---

# Przygotowanie

## Instalacja (jeśli potrzeba)

```bash
pip install requests
```

## Szkielet skryptu

Utwórz nowy skrypt `lab2_pipeline.py`. Zacznij od importów i konfiguracji — to jest rozszerzenie wzorca z Lab 1:

```python
import json
import time
import requests
from pathlib import Path

API = "https://api.dane.gov.pl/1.4"
HEADERS = {"Accept": "application/vnd.api+json"}
OUT = Path("lab2_output")
OUT.mkdir(exist_ok=True)


def save_json(data, filename):
    """Zapisuje dane do pliku JSON."""
    path = OUT / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Zapisano: {path}")
    return path
```

Nowość względem Lab 1: stała `HEADERS` — wydzielamy powtarzające się nagłówki. Funkcja `save_json` zwraca ścieżkę — przyda się w pipeline.

---

# Stronicowanie

## Przypomnienie: mechanizm stronicowania

W Lab 1 zobaczyliśmy, że odpowiedź API dane.gov.pl zawiera klucz `"links"` z adresem następnej strony:

```json
{
  "data": [...],
  "links": {
    "self": "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=5",
    "next": "https://api.dane.gov.pl/1.4/datasets?page=2&per_page=5"
  },
  "meta": {"count": 12345}
}
```

Gdy `"next"` jest obecny — jest kolejna strona. Gdy go brak (`None` lub brak klucza) — to ostatnia strona.

## Demonstracja: ręczne przejście dwóch stron

Zanim napiszemy pętlę, zobaczmy mechanizm krok po kroku:

```python
# Strona 1
r = requests.get(
    f"{API}/datasets",
    params={"page": 1, "per_page": 3},
    headers=HEADERS,
    timeout=10,
)
r.raise_for_status()
page1 = r.json()

print("Strona 1 — liczba wyników:", len(page1["data"]))
print("Następna strona:", page1["links"].get("next"))

# Strona 2 — używamy URL z links.next
next_url = page1["links"]["next"]
r2 = requests.get(next_url, headers=HEADERS, timeout=10)
r2.raise_for_status()
page2 = r2.json()

print("Strona 2 — liczba wyników:", len(page2["data"]))
```

Kluczowa obserwacja: **nie konstruujemy URL-a strony 2 ręcznie**. Używamy tego, co serwer podał w `links.next`. To jest wzorzec nawigacji po API — serwer mówi, dokąd iść dalej.

::: {.callout-note}
## Checkpoint
Czy URL z `links.next` strony 1 zgadza się z tym, co sam byś skonstruował (`?page=2&per_page=3`)? Porównaj oba.
:::

## Ćwiczenie: pętla stronicowania

Demonstracja powyżej pokazała mechanizm: pobierz stronę → weź `links.next` → pobierz następną → ... → `links.next` jest `None` → koniec.

Teraz zamknij ten mechanizm w funkcji. Poniżej jest szkielet — uzupełnij miejsca oznaczone komentarzami:

```python
def fetch_all_datasets(query, per_page=5, max_pages=None):
    """Pobiera datasety ze wszystkich stron wyników wyszukiwania.
    
    Parameters
    ----------
    query : str
        Fraza wyszukiwania.
    per_page : int
        Liczba wyników na stronę.
    max_pages : int or None
        Limit stron (None = bez limitu).
    
    Returns
    -------
    list
        Lista wszystkich datasetów (słowników z data).
    """
    url = f"{API}/datasets"
    params = {"q": query, "per_page": per_page, "page": 1}
    
    all_datasets = []
    page_num = 0
    
    while url is not None:
        page_num += 1
        
        # 1. Sprawdź, czy nie przekroczono limitu stron (max_pages).
        #    Jeśli tak — przerwij pętlę.
        # --- Twój kod ---
        
        # 2. Wyślij żądanie GET na url z params i HEADERS.
        #    Użyj raise_for_status().
        # --- Twój kod ---
        
        # 3. Sparsuj odpowiedź JSON.
        #    Wyciągnij listę datasetów (klucz "data") i dodaj do all_datasets.
        #    Wypisz postęp: numer strony, ile pobrano, ile łącznie.
        # --- Twój kod ---
        
        # 4. Ustal URL następnej strony: links.next (lub None, jeśli brak).
        #    WAŻNE: przy kolejnych stronach ustaw params = None,
        #    bo links.next to pełny URL z parametrami — nie chcesz ich podwajać.
        # --- Twój kod ---
        
        # 5. Pauza między żądaniami — nie obciążaj cudzego serwera.
        time.sleep(0.5)
    
    return all_datasets
```

::: {.callout-tip}
## Dlaczego `params = None` po pierwszej stronie?
Przy pierwszym żądaniu konstruujemy URL z parametrami (`q`, `per_page`, `page`). Ale `links.next` to **pełny URL** z parametrami już wbudowanymi. Gdybyśmy dalej przekazywali `params`, `requests` dodałby je *ponownie* — podwojone parametry.
:::

::: {.callout-tip}
## Dlaczego `time.sleep`?
To nie jest wymóg techniczny — to etykieta. API dane.gov.pl jest serwisem publicznym. Wysyłanie wielu żądań bez przerwy może obciążyć serwer i pogorszyć usługę dla innych. Pół sekundy między stronami to rozsądne minimum.
:::

Przetestuj:

```python
datasets = fetch_all_datasets("transport", per_page=5, max_pages=3)

for ds in datasets:
    print(f"  [{ds['id']}] {ds['attributes']['title']}")

save_json(datasets, "datasets_transport.json")
```

1. Czy pętla zatrzymuje się po 3 stronach (limit), nawet jeśli jest ich więcej?
2. Ile datasetów zebrałeś? Ile jest łącznie datasetów pasujących do frazy? (Sprawdź `meta.count` w dowolnej odpowiedzi API.)

---

# Retry — obsługa błędów przejściowych

## Problem

Serwer nie zawsze odpowiada poprawnie. Mogą wystąpić:

* **Timeout** — serwer nie zdążył odpowiedzieć,
* **503 Service Unavailable** — serwer chwilowo przeciążony,
* **429 Too Many Requests** — przekroczono limit zapytań,
* **Błąd połączenia** — chwilowy problem sieciowy.

Jednokrotna porażka nie oznacza, że dane są niedostępne — często wystarczy **poczekać i spróbować ponownie**.

## Wzorzec retry z backoffem

**Backoff** oznacza zwiększanie czasu oczekiwania między kolejnymi próbami. Dzięki temu nie zalewamy serwera żądaniami, gdy ma problemy:

```python
def fetch_with_retry(url, params=None, max_retries=3, backoff=1.0, timeout=10):
    """Pobiera URL z automatycznym ponawianiem przy błędach przejściowych.
    
    Parameters
    ----------
    url : str
        Adres do pobrania.
    params : dict or None
        Parametry query string.
    max_retries : int
        Maksymalna liczba prób.
    backoff : float
        Początkowy czas oczekiwania (sekundy). Podwaja się z każdą próbą.
    timeout : float
        Timeout pojedynczego żądania.
    
    Returns
    -------
    requests.Response
        Obiekt odpowiedzi (jeśli sukces).
    
    Raises
    ------
    requests.exceptions.RequestException
        Jeśli wszystkie próby się nie powiodą.
    """
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(
                url, params=params, headers=HEADERS, timeout=timeout
            )
            
            if r.status_code in (429, 503):
                wait = backoff * (2 ** (attempt - 1))
                print(f"  [{r.status_code}] Próba {attempt}/{max_retries}, "
                      f"czekam {wait:.1f}s...")
                time.sleep(wait)
                continue
            
            r.raise_for_status()
            return r
            
        except requests.exceptions.Timeout:
            wait = backoff * (2 ** (attempt - 1))
            print(f"  [Timeout] Próba {attempt}/{max_retries}, "
                  f"czekam {wait:.1f}s...")
            time.sleep(wait)
        
        except requests.exceptions.ConnectionError:
            wait = backoff * (2 ** (attempt - 1))
            print(f"  [ConnectionError] Próba {attempt}/{max_retries}, "
                  f"czekam {wait:.1f}s...")
            time.sleep(wait)
    
    raise requests.exceptions.RequestException(
        f"Nie udało się pobrać {url} po {max_retries} próbach"
    )
```

Analiza wzorca:

* **Pętla `for`** z ograniczoną liczbą prób — nigdy nie robimy nieskończonego retry.
* **Backoff wykładniczy**: 1s → 2s → 4s. Serwer dostaje czas na odzyskanie.
* **Kody 429/503**: nie rzucamy wyjątku — czekamy i próbujemy ponownie.
* **Timeout i ConnectionError**: łapiemy i ponawiamy.
* **Inne błędy** (np. 404): `raise_for_status()` rzuca wyjątek natychmiast — bo 404 się nie „naprawi" po chwili.

::: {.callout-tip}
## Retry-After
Niektóre serwery zwracają nagłówek `Retry-After` z kodem 429 lub 503 — mówi on, ile sekund czekać. Nasz kod tego nie wykorzystuje, ale w produkcyjnym kodzie warto to sprawdzić: `r.headers.get("Retry-After")` i użyć tej wartości zamiast stałego backoffu.
:::

## Ćwiczenie: test retry

Użyj httpbin do symulacji błędów:

```python
# httpbin.org/status/503 zawsze zwraca 503
try:
    r = fetch_with_retry(
        "https://httpbin.org/status/503", max_retries=3, backoff=0.5
    )
except requests.exceptions.RequestException as e:
    print(f"Ostateczny błąd: {e}")
```

1. Ile prób wykonał program? Ile łącznie czekał?
2. Zmień `max_retries` na 5. Jak zmieni się łączny czas oczekiwania?
3. Sprawdź, że `fetch_with_retry("https://httpbin.org/json")` zwraca odpowiedź bez retry.

::: {.callout-note}
## Checkpoint
Czy widzisz logi z każdej próby (numer, czas oczekiwania)? Czy program ostatecznie rzuca wyjątek po wyczerpaniu prób?
:::

---

# Pipeline: od wyszukiwania do pliku

## Czym jest pipeline

Pipeline to łańcuch kroków, w którym **wynik jednego kroku jest wejściem następnego**:

```
wyszukiwanie → lista datasetów → wybór jednego → lista zasobów → pobranie pliku
```

W Lab 1 przeszliśmy te kroki ręcznie (kopiując `id` z jednego zapytania do następnego). Teraz **automatyzujemy cały łańcuch**.

## Schemat zależności

Poniższy schemat pokazuje, które funkcje wywołują które i co przepływa między nimi:

```
fetch_all_datasets("transport", ...)
│
▼
[dataset_1, dataset_2, ...]
│
├── fetch_resources(dataset_1["id"])
│   ▼
│   [resource_A, resource_B]
│   ├── download_resource(resource_A) → plik.csv
│   └── download_resource(resource_B) → plik.xlsx
│
├── fetch_resources(dataset_2["id"])
│   ▼
│   [resource_C]
│   └── download_resource(resource_C) → plik.json
│
▼
save_json(summary) → pipeline_summary.json
```

Każdy poziom to osobna funkcja. Każda strzałka to jedno lub więcej żądań HTTP do API. Funkcja `pipeline` orkiestruje całość.

## Krok 1: zasoby datasetu

Mając `id` datasetu, pobierz jego zasoby. Korzystamy z `fetch_with_retry` — żądanie do API może się nie udać za pierwszym razem:

```python
def fetch_resources(dataset_id):
    """Pobiera listę zasobów (plików) dla danego datasetu."""
    url = f"{API}/datasets/{dataset_id}/resources"
    r = fetch_with_retry(url)
    return r.json()["data"]
```

## Krok 2: pobranie pliku

Zasoby mają w `attributes` pole `download_url` — adres pliku do pobrania. To nie jest JSON, tylko plik binarny (CSV, XLSX, itp.):

```python
def download_resource(resource, output_dir):
    """Pobiera plik zasobu i zapisuje na dysk.
    
    Parameters
    ----------
    resource : dict
        Element z listy zasobów (słownik z "attributes").
    output_dir : Path
        Katalog docelowy.
    
    Returns
    -------
    Path or None
        Ścieżka do zapisanego pliku, lub None jeśli brak URL.
    """
    attrs = resource["attributes"]
    url = attrs.get("download_url")
    
    if not url:
        print(f"  Brak download_url dla zasobu {resource['id']}")
        return None
    
    # Nazwa pliku z tytułu i formatu
    title = attrs.get("title", resource["id"])
    fmt = attrs.get("format", "bin").lower()
    filename = f"{resource['id']}_{title[:50]}.{fmt}"
    
    # Usuwamy znaki niebezpieczne w nazwie pliku
    filename = filename.replace("/", "_").replace("\\", "_")
    
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  Błąd pobierania {url}: {e}")
        return None
    
    path = output_dir / filename
    path.write_bytes(r.content)
    print(f"  Pobrano: {path} ({len(r.content)} bajtów)")
    return path
```

Zwróć uwagę na różnice względem dotychczasowego kodu:

* **`r.content`** zamiast `r.text` — pobieramy bajty (plik binarny), nie tekst.
* **`write_bytes`** zamiast `write_text` — zapis binarny.
* **Sanityzacja nazwy pliku** — usuwamy znaki, które mogłyby uszkodzić ścieżkę.
* **Obsługa braku URL** — nie każdy zasób ma `download_url`.

::: {.callout-note}
## Checkpoint
Jaka jest różnica między `r.text` a `r.content`? Kiedy używasz którego?
:::

## Krok 3: cały pipeline

Łączymy kroki w jedną funkcję. Wyszukiwanie opiera się na `fetch_all_datasets` z poprzedniej sekcji:

```python
def pipeline(query, max_datasets=3, max_files_per_dataset=2):
    """Wyszukuje datasety, pobiera zasoby i zapisuje pliki.
    
    Parameters
    ----------
    query : str
        Fraza wyszukiwania.
    max_datasets : int
        Maksymalna liczba datasetów do przetworzenia.
    max_files_per_dataset : int
        Maksymalna liczba plików na dataset.
    """
    print(f"=== Pipeline: '{query}' ===\n")
    
    # Krok 1: wyszukaj datasety
    datasets = fetch_all_datasets(query, per_page=max_datasets, max_pages=1)
    print(f"\nZnaleziono {len(datasets)} datasetów.\n")
    
    summary = []
    
    for ds in datasets[:max_datasets]:
        ds_id = ds["id"]
        title = ds["attributes"]["title"]
        print(f"--- Dataset [{ds_id}]: {title} ---")
        
        # Krok 2: pobierz zasoby
        try:
            resources = fetch_resources(ds_id)
        except requests.exceptions.RequestException as e:
            print(f"  Błąd pobierania zasobów: {e}")
            continue
        
        print(f"  Zasoby: {len(resources)}")
        
        # Krok 3: pobierz pliki
        downloaded = []
        for res in resources[:max_files_per_dataset]:
            path = download_resource(res, OUT)
            if path:
                downloaded.append(str(path))
            time.sleep(0.5)  # pauza między żądaniami — ta sama zasada co w stronicowaniu
        
        summary.append({
            "dataset_id": ds_id,
            "title": title,
            "resources_found": len(resources),
            "files_downloaded": downloaded,
        })
        
        print()
    
    # Zapisz podsumowanie
    save_json(summary, "pipeline_summary.json")
    print(f"\n=== Gotowe. Podsumowanie w pipeline_summary.json ===")
```

## Ćwiczenie: uruchom pipeline

```python
pipeline("transport", max_datasets=2, max_files_per_dataset=1)
```

1. Sprawdź katalog `lab2_output/` — czy widzisz pobrane pliki?
2. Otwórz `pipeline_summary.json` — czy zawiera informacje o pobranych plikach?
3. Zmień frazę wyszukiwania na inną (np. `"szkoły"`, `"powietrze"`).
4. Co się stanie, gdy dataset nie ma zasobów z `download_url`?

::: {.callout-note}
## Checkpoint
Czy Twój pipeline obsługuje sytuację, gdy zasób nie ma `download_url`? Czy brak jednego pliku nie zatrzymuje całego procesu?
:::

---

# Zadania samodzielne

## Zadanie A: stronicowanie z limitem wyników

Napisz funkcję `fetch_datasets_until(query, target_count, per_page=10)`, która:

1. Pobiera strony wyników, aż zbierze **co najmniej `target_count` datasetów** (lub strony się skończą).
2. Zwraca listę datasetów (może być dłuższa niż `target_count`, jeśli ostatnia strona dodała nadmiar).
3. Wypisuje na bieżąco: numer strony, liczbę pobranych na stronie, łączną liczbę.

Przetestuj: `fetch_datasets_until("szkoły", 25, per_page=10)`.

## Zadanie B: statystyki zasobów

Dla wybranej frazy wyszukiwania:

1. Pobierz pierwsze 10 datasetów.
2. Dla każdego pobierz listę zasobów.
3. Zbierz statystyki: ile zasobów ma każdy format (`CSV`, `JSON`, `XLSX`, itp.).
4. Wypisz podsumowanie: format → liczba zasobów.
5. Zapisz statystyki do `format_stats.json`.

Wskazówka: użyj słownika do zliczania (`dict` z `.get(key, 0) + 1` lub `collections.Counter`).

## Zadanie C (dodatkowe): odporny pipeline

Rozbuduj pipeline tak, żeby:

1. Używał `fetch_with_retry` **wszędzie** (wyszukiwanie, zasoby, pobieranie plików).
2. Logował każdy błąd do listy `errors` (zamiast przerywać).
3. Na końcu zapisywał zarówno `summary.json` (sukcesy), jak i `errors.json` (porażki).
4. Wypisywał podsumowanie: „Pobrano X plików, Y błędów".

---

# Podsumowanie

W tym labie:

* napisałeś pętlę stronicowania — automatyczne przechodzenie po stronach wyników API,
* zaimplementowałeś wzorzec retry z backoffem wykładniczym — odporność na błędy przejściowe,
* zbudowałeś pipeline: wyszukiwanie → zasoby → pobranie pliku — pełen łańcuch automatycznej akwizycji danych,
* pobrałeś realne pliki danych (CSV, XLSX) z API dane.gov.pl,
* rozbudowałeś funkcje wielokrotnego użytku (`fetch_with_retry`, `fetch_all_datasets`).

W następnych zajęciach: budujemy własny serwer HTTP (Flask) — kontrolowane środowisko, na którym będziemy ćwiczyć parsowanie HTML i crawling.