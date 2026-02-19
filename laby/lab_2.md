---
title: "Lab 2: Nawigacja po API i automatyzacja pobierania danych"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---

# Cel 

Zakres materiału:

* przechodzenie pełnego pipeline'u: wyszukanie datasetu → pobranie metadanych → pobranie realnego pliku danych,
* iteracja po stronach wyników API (stronicowanie w pętli),
* zapisywanie pobranych danych do plików (JSON, CSV, binarne),
* budowanie funkcji opakowujących zapytania HTTP z obsługą błędów.

Wymagania wstępne: ukończony Lab 1 (umiesz wysłać `GET` przez `requests`, znasz strukturę JSON:API, korzystałeś ze Swaggera).

---

# Powtórka — sesja robocza

## Przygotowanie

Utwórz folder roboczy i otwórz notatnik Jupyter lub skrypt `.py`.

```python
import requests
from pathlib import Path

API = "https://api.dane.gov.pl/1.4"
HEADERS = {"Accept": "application/vnd.api+json"}
TIMEOUT = 15

# folder na pobrane pliki
OUT = Path("lab_2_output")
OUT.mkdir(exist_ok=True)
```

Stałe `API`, `HEADERS`, `TIMEOUT` definiujemy raz — dzięki temu nie powtarzamy ich w każdym zapytaniu.

## Szybki test połączenia

```python
r = requests.get(f"{API}/datasets", params={"page": 1, "per_page": 1},
                 headers=HEADERS, timeout=TIMEOUT)
r.raise_for_status()
print("OK, status:", r.status_code)
```

::: checkpoint
**Checkpoint:** Jeśli widzisz `OK, status: 200` — środowisko działa. Jeśli nie — sprawdź połączenie z internetem i poprawność URL-a.
:::

---

# Funkcja pomocnicza do zapytań

W Labie 1 powtarzaliśmy ten sam wzorzec: `requests.get(...)`, `raise_for_status()`, `.json()`. Zamknijmy go w funkcji, żeby reszta kodu była czytelniejsza.

```python
def api_get(endpoint, params=None):
    """Wysyła GET do API dane.gov.pl i zwraca sparsowany JSON.
    
    Parameters
    ----------
    endpoint : str
        Ścieżka względem API, np. "/datasets" lub "/datasets/830/resources".
    params : dict, optional
        Parametry query string.
    
    Returns
    -------
    dict
        Sparsowana odpowiedź JSON.
    
    Raises
    ------
    requests.exceptions.HTTPError
        Gdy serwer zwróci kod 4xx lub 5xx.
    requests.exceptions.Timeout
        Gdy serwer nie odpowie w ciągu TIMEOUT sekund.
    """
    url = f"{API}{endpoint}"
    r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
```

Od teraz zamiast pisać pełne zapytanie, możemy:

```python
data = api_get("/datasets", {"page": 1, "per_page": 5})
print(len(data["data"]), "datasetów")
```

::: key-concept
**Dlaczego warto?** W dalszej części labu będziemy wysyłać dziesiątki zapytań. Funkcja `api_get` eliminuje powtórzenia i daje jedno miejsce, w którym można dodać np. logowanie, retry, czy cache.
:::

---

# Pipeline — od wyszukiwania do pliku

Teraz przejdziemy pełną ścieżkę, jaką typowo pokonuje się przy automatycznym pobieraniu danych z API:

```
wyszukaj datasety → wybierz jeden → pobierz metadane zasobów → pobierz plik
```

## Krok 1: wyszukiwanie

Szukamy datasetów związanych z wybranym tematem. Parametr wyszukiwania to `q` (możesz to sprawdzić w Swaggerze).

```python
query = "jakość powietrza"

data = api_get("/datasets", {"q": query, "per_page": 5})
results = data["data"]

print(f"Znaleziono {data['meta']['count']} wyników, wyświetlam {len(results)}:\n")
for ds in results:
    a = ds["attributes"]
    print(f"  [{ds['id']}] {a['title']}")
    print(f"       kategoria: {a.get('category', '?')}, "
          f"zasoby: {a.get('resources_count', '?')}")
    print()
```

Wybierz dataset, który ma przynajmniej kilka zasobów (`resources_count` > 0).

## Krok 2: szczegóły datasetu

```python
DATASET_ID = "..."  # ← wklej id z kroku 1

ds_data = api_get(f"/datasets/{DATASET_ID}")
ds = ds_data["data"]
attrs = ds["attributes"]

print("Tytuł:", attrs["title"])
print("Opis:", attrs.get("notes", "(brak)")[:300])
print("Licencja:", attrs.get("license_condition_db_or_copyrighted"))
```

## Krok 3: lista zasobów

```python
res_data = api_get(f"/datasets/{DATASET_ID}/resources")
resources = res_data["data"]

print(f"Zasoby ({len(resources)}):\n")
for res in resources:
    ra = res["attributes"]
    print(f"  [{res['id']}] {ra.get('title', '(bez tytułu)')}")
    print(f"       format: {ra.get('format', '?')}, "
          f"rozmiar: {ra.get('file_size', '?')}")
    print()
```

## Krok 4: metadane zasobów jako CSV

API dane.gov.pl umożliwia pobranie metadanych zasobów jako plik CSV. To nie jest odpowiedź JSON:API — to zwykły plik CSV.

```python
csv_url = f"{API}/datasets/{DATASET_ID}/resources/metadata.csv"

r = requests.get(csv_url, params={"lang": "en"}, timeout=TIMEOUT)
r.raise_for_status()

csv_path = OUT / f"resources_{DATASET_ID}_metadata.csv"
csv_path.write_text(r.text, encoding="utf-8")
print(f"Zapisano: {csv_path} ({len(r.text)} znaków)")
```

Podgląd:

```python
import pandas as pd

df = pd.read_csv(csv_path, sep=";")
print("Kolumny:", list(df.columns))
print(f"Wiersze: {len(df)}\n")
df[["Resource title", "File format", "File size", "Download URL"]].head()
```

::: checkpoint
**Checkpoint:** Czy widzisz kolumnę `Download URL` z adresami do pobrania plików? Jeśli kolumna jest pusta albo nie istnieje — wybierz inny dataset z kroku 1 i powtórz od kroku 2.
:::

## Krok 5: pobranie realnego pliku danych

Wybierz jeden adres z kolumny `Download URL`:

```python
download_url = df["Download URL"].dropna().iloc[0]
print("Pobieram:", download_url)
```

Pobieranie pliku binarnego (z obsługą przekierowań — `requests` robi to domyślnie):

```python
r = requests.get(download_url, timeout=30)
r.raise_for_status()

# nazwa pliku z nagłówka lub z URL-a
filename = download_url.split("/")[-1] or "downloaded_file"
file_path = OUT / filename

file_path.write_bytes(r.content)
print(f"Zapisano: {file_path} ({len(r.content)} bajtów)")
```

::: key-concept
**Uwaga o dużych plikach.** Powyższy kod wczytuje cały plik do pamięci (`r.content`). Dla plików większych niż ~100 MB lepiej pobierać strumieniowo:

```python
with requests.get(download_url, stream=True, timeout=30) as r:
    r.raise_for_status()
    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
```

Na potrzeby tego labu zwykłe pobranie wystarczy.
:::

::: checkpoint
**Checkpoint:** Przeszedłeś pełny pipeline: wyszukiwanie → dataset → zasoby → metadane CSV → pobranie pliku. To jest rdzeń automatycznego pozyskiwania danych z API.
:::

---

# Stronicowanie — iteracja po wielu stronach

API dane.gov.pl zwraca wyniki stronicowane. Na jednej stronie jest najwyżej `per_page` wyników (domyślnie 20). Żeby pobrać wszystkie, trzeba iterować po stronach.

## Podejście 1: pętla po numerach stron

```python
page = 1
per_page = 5
all_datasets = []

while True:
    data = api_get("/datasets", {"page": page, "per_page": per_page})
    items = data["data"]
    
    if not items:
        break
    
    all_datasets.extend(items)
    print(f"Strona {page}: pobrano {len(items)} datasetów "
          f"(łącznie: {len(all_datasets)})")
    
    # sprawdź, czy jest następna strona
    next_link = data.get("links", {}).get("next")
    if next_link is None:
        break
    
    page += 1
    
    # bezpiecznik: nie pobieraj więcej niż 5 stron w tym ćwiczeniu
    if page > 5:
        print("Przerwano po 5 stronach (bezpiecznik).")
        break

print(f"\nPobrano łącznie: {len(all_datasets)} datasetów")
```

## Podejście 2: podążanie za linkiem `next`

Zamiast ręcznie zwiększać `page`, można podążać za adresem `next` z odpowiedzi. To jest bardziej odporny wzorzec — nie zakłada, że numeracja stron zaczyna się od 1 ani że jest ciągła.

```python
url = f"{API}/datasets"
params = {"per_page": 5}
all_datasets = []
page_count = 0

while url is not None:
    r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    
    all_datasets.extend(data["data"])
    page_count += 1
    print(f"Strona {page_count}: +{len(data['data'])} "
          f"(łącznie: {len(all_datasets)})")
    
    # następna strona — link jest pełnym URL-em
    url = data.get("links", {}).get("next")
    params = None  # parametry są już wbudowane w URL z linku next
    
    if page_count >= 5:
        print("Przerwano po 5 stronach (bezpiecznik).")
        break
```

::: key-concept
**Bezpiecznik** (`if page >= N: break`) jest ważny przy nauce i debugowaniu. API dane.gov.pl ma tysiące datasetów — bez limitu pętla potrwa bardzo długo i obciąży serwer. W kodzie produkcyjnym bezpiecznik zastąpisz właściwym warunkiem stopu (np. „pobierz wszystkie do 2024 roku").
:::

::: checkpoint
**Checkpoint:** Czy obie metody dały te same `id` datasetów? Porównaj:

```python
# zakładając, że wyniki z podejścia 1 są w all_datasets_v1,
# a z podejścia 2 w all_datasets_v2:
ids_v1 = [d["id"] for d in all_datasets_v1]
ids_v2 = [d["id"] for d in all_datasets_v2]
print("Identyczne:", ids_v1 == ids_v2)
```
:::

---

# Odporność na błędy — retry

W praktyce zapytania do API mogą się nie powieść z powodów przejściowych: serwer jest chwilowo przeciążony (503), przekroczono limit zapytań (429), albo sieć „czkawkała" (timeout). Rozsądną strategią jest **ponowienie** (retry) po krótkiej przerwie.

## Prosta funkcja z retry

```python
import time

def api_get_retry(endpoint, params=None, max_retries=3, backoff=2.0):
    """GET z automatycznym ponawianiem przy błędach przejściowych."""
    url = f"{API}{endpoint}"
    
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", backoff * attempt))
                print(f"  429 Too Many Requests, czekam {wait}s...")
                time.sleep(wait)
                continue
            
            r.raise_for_status()
            return r.json()
        
        except requests.exceptions.Timeout:
            print(f"  Timeout (próba {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(backoff * attempt)
        
        except requests.exceptions.HTTPError as e:
            if r.status_code >= 500:
                print(f"  Błąd serwera {r.status_code} (próba {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(backoff * attempt)
            else:
                raise  # 4xx (poza 429) — nie ponawiamy
    
    raise RuntimeError(f"Nie udało się pobrać {url} po {max_retries} próbach")
```

Kluczowe elementy:

* **429 (Too Many Requests)** — serwer mówi „za szybko"; czekamy tyle, ile każe nagłówek `Retry-After` (lub domyślnie),
* **5xx (błąd serwera)** — problem po stronie serwera, warto spróbować ponownie,
* **4xx (poza 429)** — błąd klienta (np. 404), ponawianie nie pomoże, od razu rzucamy wyjątek,
* **backoff** — czas oczekiwania rośnie z każdą próbą (2s, 4s, 6s), żeby nie zalewać serwera.

Test:

```python
# powinno działać normalnie
data = api_get_retry("/datasets", {"page": 1, "per_page": 2})
print("OK:", data["data"][0]["attributes"]["title"])

# powinno rzucić wyjątek (404, nie ponawiamy)
try:
    api_get_retry("/datasets/999999999")
except requests.exceptions.HTTPError as e:
    print("Błąd (zgodnie z oczekiwaniem):", e)
```

::: checkpoint
**Checkpoint:** Czy rozumiesz, dlaczego 404 nie jest ponawiane, a 503 tak? W automatyzacji to rozróżnienie decyduje o tym, czy skrypt „zawiesza się" na godzinę, czy szybko informuje o prawdziwym problemie.
:::

---

# Zadania samodzielne

## Zadanie A: zbierz tytuły z N stron

Napisz funkcję `collect_titles(n_pages, per_page=10)`, która:

1. Pobiera `n_pages` stron listy datasetów.
2. Zwraca listę słowników `{"id": ..., "title": ...}` ze wszystkich pobranych wyników.
3. Używa `api_get` lub `api_get_retry`.

Przetestuj z `n_pages=3, per_page=10` i wypisz wyniki.

## Zadanie B: pipeline wyszukiwanie → pobranie pliku

Napisz skrypt (lub funkcję), który:

1. Wyszukuje datasety po wybranym słowie kluczowym (`q=...`).
2. Dla pierwszego znalezionego datasetu pobiera listę zasobów.
3. Wybiera pierwszy zasób w formacie CSV (lub innym, który ma `Download URL`).
4. Pobiera plik i zapisuje go do katalogu `lab_2_output/`.
5. Wypisuje podsumowanie: tytuł datasetu, tytuł zasobu, rozmiar pobranego pliku.

Wskazówka: metadane w CSV (`metadata.csv?lang=en`) zawierają kolumnę `Download URL`. Możesz z niej skorzystać lub znaleźć URL w odpowiedzi JSON zasobów (pole `link` w `attributes`).

## Zadanie C: stronicowanie z warunkiem stopu

Napisz funkcję `search_all(query, max_results=50)`, która:

1. Wyszukuje datasety po frazie `query`.
2. Iteruje po stronach, aż zbierze `max_results` wyników **lub** skończą się strony.
3. Zwraca listę zebranych datasetów.

Przetestuj na kilku frazach i porównaj `meta["count"]` (ile jest łącznie) z liczbą faktycznie pobranych wyników.

## Zadanie D (dodatkowe): pobranie wielu plików

Rozszerz pipeline z Zadania B:

1. Dla wybranego datasetu pobierz **wszystkie** zasoby (nie tylko pierwszy).
2. Każdy zasób zapisz do osobnego pliku w `lab_2_output/{dataset_id}/`.
3. Na końcu wypisz tabelę podsumowującą: tytuł zasobu, format, rozmiar pobranego pliku, status (OK / błąd).
4. Dodaj obsługę błędów — jeśli pobranie jednego zasobu się nie uda, kontynuuj z następnym.

---

# Podsumowanie

W tym labie:

* zbudowałeś funkcję pomocniczą `api_get` eliminującą powtórzenia,
* przeszedłeś pełny pipeline: wyszukiwanie → metadane → pobranie pliku,
* opanowałeś dwa wzorce stronicowania (numeracja stron / podążanie za `next`),
* napisałeś funkcję z retry i zróżnicowaną obsługą kodów błędów,
* automatyzowałeś pozyskiwanie danych w zadaniach samodzielnych.

Masz teraz narzędzia, żeby pobierać dane z dowolnego API opartego na HTTP i REST. W kolejnych zajęciach: web scraping (dane ze stron, które nie mają API) i praca z formatami danych.