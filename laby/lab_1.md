---
title: "Lab 1: Klienci HTTP (curl, requests)"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Wysyłanie żądań HTTP do publicznego API i odbieranie odpowiedzi w Pythonie,
* Rozpoznawanie w odpowiedzi kodu statusu, nagłówków i ciała (JSON),
* Korzystanie z interaktywnej dokumentacji API (Swagger),
* Poruszanie się po strukturze JSON:API: listy, obiekty, pola `data`, `attributes`, `links`.

Narzędzia: Python (`requests`), `curl` (krótko, jako narzędzie diagnostyczne), przeglądarka.

---

# Czym jest API dane.gov.pl

## Portal i API

[dane.gov.pl](https://dane.gov.pl/) to polski portal otwartych danych publicznych. Publikuje zbiory danych (datasety) udostępniane przez instytucje państwowe — od jakości powietrza, przez rejestry szkół, po rozkłady jazdy.

Portal udostępnia **API** (Application Programming Interface) — interfejs, przez który program komputerowy może pobierać te same dane, które widzisz na stronie, ale w formacie nadającym się do automatycznego przetwarzania (JSON zamiast HTML).

Adres bazowy API: `https://api.dane.gov.pl/1.4`

Numer `1.4` to wersja API. Gdyby się zmieniła, wystarczy podmienić go w jednym miejscu.

## Mapa zasobów API

API dane.gov.pl organizuje dane w hierarchię, którą najłatwiej zrozumieć jako zagnieżdżone kolekcje:

```
/datasets                        ← kolekcja: lista wszystkich zbiorów danych
/datasets/{id}                   ← element: szczegóły jednego zbioru
/datasets/{id}/resources         ← kolekcja zagnieżdżona: zasoby (pliki) w zbiorze
/datasets/{id}/resources/{rid}   ← element: metadane jednego zasobu
```

To jest dokładnie wzorzec **kolekcja / element / podzasób**, który poznałeś na wykładzie.

Przykładowo:

* `GET /1.4/datasets?page=1&per_page=5` — pobierz pierwszych 5 zbiorów (kolekcja, stronicowana),
* `GET /1.4/datasets/830` — pobierz szczegóły zbioru o `id` = 830,
* `GET /1.4/datasets/830/resources` — pobierz listę zasobów zbioru 830.

## Format odpowiedzi: JSON:API

API dane.gov.pl używa standardu **JSON:API** (specyfikacja: [jsonapi.org](https://jsonapi.org/)). W praktyce oznacza to, że odpowiedzi mają stałą strukturę:

```json
{
  "data": [
    {
      "id": "830",
      "type": "dataset",
      "attributes": {
        "title": "Wykaz szkół i placówek oświatowych",
        "notes": "Rejestr Szkół i Placówek Oświatowych ...",
        "category": "Education",
        "modified": "2025-01-15T10:32:00Z"
      },
      "relationships": { ... },
      "links": {
        "self": "https://api.dane.gov.pl/1.4/datasets/830"
      }
    },
    ...
  ],
  "links": {
    "self":  "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=5",
    "next":  "https://api.dane.gov.pl/1.4/datasets?page=2&per_page=5",
    "last":  "https://api.dane.gov.pl/1.4/datasets?page=..."
  },
  "meta": {
    "count": 12345
  }
}
```

Co warto zapamiętać:

* **`data`** — lista (lub pojedynczy obiekt) z wynikami; to jest główna część odpowiedzi,
* **`id`** i **`type`** — identyfikator i typ zasobu,
* **`attributes`** — słownik z właściwymi danymi (tytuł, opis, kategoria itd.),
* **`links`** — adresy do nawigacji (stronicowanie, powiązane zasoby),
* **`meta`** — metadane (np. łączna liczba wyników).

Nagłówek `Accept: application/vnd.api+json` informuje serwer, że klient oczekuje odpowiedzi w formacie JSON:API. Jeśli go nie podasz, serwer dane.gov.pl i tak zwróci JSON — ale dobrą praktyką jest podawać go jawnie.

## Dokumentacja interaktywna (Swagger)

Zanim napiszesz pierwsze zapytanie, warto wiedzieć **gdzie szukać informacji** o endpointach, parametrach i formatach odpowiedzi.

API dane.gov.pl ma dokumentację Swagger pod adresem:

> **<https://api.dane.gov.pl/doc>**

Swagger UI to interaktywna strona, na której możesz:

* przeglądać listę endpointów (pogrupowanych tematycznie),
* sprawdzić jakie parametry przyjmuje dany endpoint,
* wypróbować zapytanie bezpośrednio w przeglądarce (przycisk **Try it out → Execute**).

### Czytanie Swaggera

Otwórz w przeglądarce `https://api.dane.gov.pl/doc` i wykonaj po kolei:

1. Znajdź sekcję dotyczącą **Datasets**.
2. Rozwiń endpoint **`GET /1.4/datasets`**.
3. Przejrzyj listę parametrów. Zwróć uwagę na:
    * `page` — numer strony,
    * `per_page` — liczba wyników na stronę,
    * `q` — fraza wyszukiwania,
    * `sort` — kryterium sortowania.
4. Kliknij **Try it out**.
5. Ustaw `per_page` na `2`, **wyczyść pozostałe pola**, jeśli Swagger coś w nich dopisał automatycznie (zobacz uwagę poniżej).
6. Kliknij **Execute**.
7. W sekcji **Response body** zobaczysz odpowiedź JSON. Zwróć uwagę na strukturę `data → [{ id, type, attributes }]`.
8. W sekcji **Curl** Swagger pokaże polecenie `curl`:
    * jeśli jest bardzo długie (z parametrami typu `id[gt]`, `id[lt]`, `title[...]`, `description[...]` itd.), potraktuj je jako „szablon” i **usuń z URL-a wszystkie te automatycznie dodane filtry**, zostawiając tylko to, co ustawiłeś ręcznie (np. `page` i `per_page`).

::: {.callout-warning}
## Uwaga dotycząca Swaggera
Swagger często wypełnia „pusty formularz” przykładowymi wartościami **we wszystkich** polach naraz (zwłaszcza tam, gdzie parametr jest obiektem filtrów typu `term/terms/gt/lt/gte/lte/...`). To jest artefakt UI, nie wymaganie API. W praktyce zostawiasz tylko te pola, których faktycznie chcesz użyć (zwykle: `page`, `per_page`; ewentualnie *jeden* operator na pole).
:::

::: {.callout-note}
## Checkpoint
Czy widzisz pole `data` z listą obiektów? Czy potrafisz wskazać `id` i `title` pierwszego datasetu? Zapisz sobie jedno `id` — przyda się za chwilę.
:::

---

# Szczegóły HTTP (curl)

Zanim przejdziemy do Pythona, użyjemy `curl` do zobaczenia „surowego" HTTP — tego, co zwykle jest ukryte za bibliotekami.

## Przygotowanie

Sprawdź, czy masz `curl` (w terminalu / PowerShell):

```bash
curl --version
```

Uwaga (Windows): jeśli pracujesz w PowerShell, używaj `curl.exe` zamiast `curl` (które bywa aliasem do innego polecenia).

## Surowa odpowiedź HTTP

Pobierz stronę i wyświetl **nagłówki + ciało** razem:

```bash
curl -i "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=2"
```

Na ekranie zobaczysz coś w rodzaju:

```
HTTP/2 200
content-type: application/vnd.api+json
...

{"data":[{"id":"...", ...}], ...}
```

::: {.callout-note}
Widzisz linię statusu (`HTTP/2 200`), nagłówki odpowiedzi (w tym `content-type`), pustą linię, a potem ciało odpowiedzi (JSON). To jest dokładnie struktura odpowiedzi HTTP z wykładu.
:::

## Tryb diagnostyczny

Dodaj flagę `-v` (verbose), żeby zobaczyć **też żądanie**, które wysłał twój klient:

```bash
curl -v "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=1"
```

W trybie `-v` `curl` oznacza różne typy linii prefiksami:

- Linie zaczynające się od `*` to **informacje diagnostyczne klienta** (np. rozwiązywanie DNS, próba połączenia, TLS/HTTPS handshake, negocjacja HTTP/2, przekierowania, uwagi typu „Connection #0 left intact”).
- Linie zaczynające się od `>` to **żądanie** wysyłane przez ciebie (linia `GET ...` oraz nagłówki żądania).
- Linie zaczynające się od `<` to **odpowiedź serwera** (status i nagłówki odpowiedzi).

Uwaga: **ciało odpowiedzi** (np. JSON) zwykle pojawia się jako „zwykły” tekst **bez** prefiksów `>`, `<`, `*` — jest wypisywane na standardowe wyjście, podczas gdy log `-v` idzie na standardowy błąd. Dlatego w terminalu widzisz to wymieszane czasowo, ale logicznie to są dwa strumienie.

Znajdź w części `>` linię `GET /1.4/datasets?...` oraz nagłówek `Host:`. W części `<` znajdź `content-type:` i kod statusu (np. `200`).


## Sama odpowiedź, ładnie sformatowana

```bash
curl -s "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=2" | python3 -m json.tool | head -40
```

Pipe przez `python3 -m json.tool` formatuje JSON z wcięciami. Flaga `-s` wycisza pasek postępu.

::: {.callout-note}
## Checkpoint
Potrafisz wskazać w wyjściu `curl -i` kod statusu, `Content-Type` i początek ciała JSON?
:::

---

# Zapytania HTTP w Pythonie (requests)

Od tego momentu pracujemy w Pythonie. Otwórz nowy notatnik Jupyter lub skrypt `.py` w Thonnym.

## Instalacja (jeśli potrzeba)

Biblioteka `requests` jest standardem do wysyłania zapytań HTTP w Pythonie, nie jest jednak częścią biblioteki standardowej, więc może wymagać instalacji:

```bash
pip install requests
```

## Pierwsze żądanie GET

```python
import requests

url = "https://example.com"
r = requests.get(url)

print("Status:", r.status_code)
print("Content-Type:", r.headers.get("Content-Type"))
print("Treść (100 znaków):", r.text[:100])
```

Obiekt `r` (obiekt klasy `Response`) zawiera całą odpowiedź HTTP:

* `r.status_code` — kod statusu (int, np. `200`),
* `r.headers` — słownik nagłówków odpowiedzi,
* `r.text` — ciało jako tekst (str),
* `r.content` — ciało jako bajty (bytes),
* `r.json()` — ciało sparsowane z JSON do dict/list.

## Parametry zapytania (query string)

Zamiast sklejać URL ręcznie, podaj parametry jako słownik:

```python
r = requests.get(
    "https://httpbin.org/get",
    params={"q": "python", "page": 1}
)
print("Pełny URL:", r.url)
# → https://httpbin.org/get?q=python&page=1
```

`requests` sam zakoduje wartości i doda `?...&...` do URL.

## Nagłówki żądania

Nagłówki podajesz przez parametr `headers`:

```python
r = requests.get(
    "https://httpbin.org/headers",
    headers={"Accept": "application/json", "User-Agent": "MojSkrypt/1.0"}
)
print(r.json())
```

## Odbieranie JSON

```python
r = requests.get("https://httpbin.org/json")

print("Status:", r.status_code)
print("Content-Type:", r.headers.get("Content-Type"))

data = r.json()           # parsuje JSON → dict
print("Typ:", type(data))
print("Klucze:", list(data.keys()))
```

::: {.callout-tip}
## Ważne
`r.json()` rzuci wyjątek, jeśli ciało odpowiedzi nie jest poprawnym JSON-em (np. gdy serwer zwrócił HTML ze stroną błędu). Dlatego przed parsowaniem warto sprawdzić `r.status_code` lub użyć `r.raise_for_status()`.
:::

## Bezpieczny wzorzec: sprawdzaj przed parsowaniem

```python
r = requests.get("https://httpbin.org/json", timeout=10)
r.raise_for_status()  # rzuci wyjątek przy 4xx / 5xx
data = r.json()
```

Metoda `raise_for_status()` zamienia kody błędów na wyjątek Pythona — dzięki temu nie próbujesz parsować odpowiedzi z błędem.

::: {.callout-note}
## Checkpoint
Wykonaj `requests.get("https://httpbin.org/json")` i wypisz `status_code`, `Content-Type` z nagłówków, oraz klucze (keys) sparsowanego JSON-a. Czy wszystko się zgadza?
:::

---

# Zapytanie do API dane.gov.pl

Teraz łączymy to, co wiemy o `requests`, ze strukturą API, którą poznaliśmy w Części 1.

## Krok 1: lista datasetów

```python
import requests

API = "https://api.dane.gov.pl/1.4"

r = requests.get(
    f"{API}/datasets",
    params={"page": 1, "per_page": 5},
    headers={"Accept": "application/vnd.api+json"},
    timeout=10,
)
r.raise_for_status()

data = r.json()
print("Klucze odpowiedzi:", list(data.keys()))
```

Spodziewane klucze: `data`, `links`, `meta` (ewentualnie `included`).

## Krok 2: eksploracja struktury

```python
# Ile datasetów na tej stronie?
datasets = data["data"]
print("Liczba datasetów:", len(datasets))

# Pierwszy dataset — co zawiera?
first = datasets[0]
print("Klucze obiektu:", list(first.keys()))
print("ID:", first["id"])
print("Typ:", first["type"])
print("Tytuł:", first["attributes"]["title"])
```

## Krok 3: przegląd wszystkich wyników

```python
for ds in datasets:
    ds_id = ds["id"]
    title = ds["attributes"]["title"]
    print(f"  [{ds_id}] {title}")
```

## Krok 4: linki nawigacyjne (stronicowanie)

```python
print("Linki:", data.get("links", {}))
print("Meta:", data.get("meta", {}))
```

W polu `links` powinien pojawić się klucz `next` z URL-em następnej strony. W polu `meta` — łączna liczba zbiorów (`count`).

::: {.callout-note}
## Checkpoint
Czy widzisz listę 5 datasetów z ich `id` i tytułami? Czy w `links` jest adres `next`? Zapisz `id` jednego datasetu, który wydaje ci się ciekawy.
:::

## Krok 5: szczegóły wybranego datasetu

Podstaw `id` z poprzedniego kroku:

```python
DATASET_ID = "..."   # ← wklej tu swoje id

r = requests.get(
    f"{API}/datasets/{DATASET_ID}",
    headers={"Accept": "application/vnd.api+json"},
    timeout=10,
)
r.raise_for_status()

ds = r.json()["data"]
attrs = ds["attributes"]

print("Tytuł:", attrs["title"])
print("Opis:", attrs.get("notes", "(brak)")[:200])
print("Kategoria:", attrs.get("category"))
print("Modyfikacja:", attrs.get("modified"))
```

Zwróć uwagę: dla kolekcji `data` jest **listą**, a dla pojedynczego elementu — **słownikiem**.

## Krok 6: zasoby (resources) datasetu

```python
r = requests.get(
    f"{API}/datasets/{DATASET_ID}/resources",
    headers={"Accept": "application/vnd.api+json"},
    timeout=10,
)
r.raise_for_status()

resources = r.json()["data"]
print(f"Liczba zasobów: {len(resources)}\n")

for res in resources:
    res_attrs = res["attributes"]
    print(f"  [{res['id']}] {res_attrs.get('title', '(bez tytułu)')}")
    print(f"       format: {res_attrs.get('format', '?')}")
    print()
```

Jeśli lista zasobów jest pusta, wybierz inny dataset i powtórz od kroku 5.

::: {.callout-note}
## Checkpoint
Czy widzisz listę zasobów z ich `id`, tytułami i formatami? Jeśli tak — udało ci się przejść pełny łańcuch: kolekcja → element → podzasoby. To jest główna umiejętność tego labu.
:::

---

# Obsługa błędów

## Błąd 404: nieistniejący zasób

```python
r = requests.get(
    f"{API}/datasets/999999999",
    headers={"Accept": "application/vnd.api+json"},
    timeout=10,
)

print("Status:", r.status_code)
print("Content-Type:", r.headers.get("Content-Type"))
print("Treść:", r.text[:300])
```

Serwer powinien zwrócić `404`. Zwróć uwagę, że odpowiedź nadal ma ciało — serwer wysyła komunikat o błędzie (zwykle w JSON).

## Co robi `raise_for_status()` przy 404?

```python
try:
    r.raise_for_status()
except requests.exceptions.HTTPError as e:
    print("Wyjątek:", e)
```

## Timeout

```python
try:
    r = requests.get(f"{API}/datasets", params={"page": 1}, timeout=0.001)
except requests.exceptions.Timeout:
    print("Przekroczono limit czasu!")
except requests.exceptions.RequestException as e:
    print("Inny błąd:", e)
```

Ustawiamy absurdalnie krótki timeout (`0.001` s), żeby wymusić błąd. W praktyce sensowna wartość to 5–30 sekund.

::: {.callout-tip}
## Wzorzec minimalny do zapamiętania

```python
try:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
except requests.exceptions.Timeout:
    print("Timeout")
except requests.exceptions.HTTPError as e:
    print("Błąd HTTP:", e)
except requests.exceptions.RequestException as e:
    print("Błąd połączenia:", e)
```
:::

::: {.callout-note}
## Checkpoint
Czy umiesz rozróżnić trzy sytuacje: odpowiedź 200 (sukces), odpowiedź 404 (błąd serwera w sensie „nie znaleziono"), wyjątek Timeout (brak odpowiedzi)? To jest kluczowe w automatyzacji.
:::

---

# Zadania samodzielne

## Zadanie A: wyszukiwanie datasetów

W dokumentacji Swagger (`https://api.dane.gov.pl/doc`) znajdź parametr, który pozwala wyszukiwać datasety po frazie (słowie kluczowym).

1. Wykonaj wyszukiwanie po wybranym słowie (np. `"transport"`, `"szkoły"`, `"powietrze"`).
2. Wypisz `id` i `title` wyników.
3. Wybierz jeden dataset z wyników i pobierz jego szczegóły (`/datasets/{id}`).
4. Pobierz listę zasobów tego datasetu (`/datasets/{id}/resources`).
5. Wypisz tytuły i formaty zasobów.

## Zadanie B: porównanie dwóch stron wyników

1. Pobierz stronę 1 i stronę 2 listy datasetów (np. `per_page=5`).
2. Wypisz `id` datasetów z obu stron.
3. Sprawdź (programowo lub ręcznie), że zbiory `id` się nie pokrywają.
4. Wypisz adres `next` z linków pierwszej strony i porównaj go z URL-em, który sam skonstruowałeś dla strony 2.

## Zadanie C (dodatkowe): metadane zasobów w CSV

API dane.gov.pl pozwala pobrać metadane zasobów danego datasetu jako CSV:

```
GET /1.4/datasets/{id}/resources/metadata.csv?lang=en
```

1. Pobierz ten plik za pomocą `requests` (uwaga: to nie jest JSON, tylko CSV — użyj `r.text` zamiast `r.json()`).
2. Zapisz odpowiedź do pliku `.csv`.
3. Wczytaj plik do `pandas.DataFrame` i wypisz nazwy kolumn.
4. Znajdź kolumnę `Download URL` — zawiera adresy do pobrania realnych plików danych.

---

# Podsumowanie

W tym labie:

* poznałeś API dane.gov.pl i jego hierarchię zasobów,
* zobaczyłeś surowe HTTP w `curl` (nagłówki, kody statusu),
* nauczyłeś się wysyłać zapytania GET w `requests` i parsować odpowiedzi JSON:API,
* przeszedłeś pełny łańcuch: kolekcja → element → podzasoby,
* obsłużyłeś błędy HTTP (404, timeout).

W następnym labie: nawigacja po wielu stronach wyników (pętla po API), pobieranie realnych plików danych i budowanie pierwszego pipeline'u automatycznego pozyskiwania danych.