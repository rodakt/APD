---
title: "Lab 1: Klienci HTTP (curl, requests)"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Wysyłanie żądań HTTP do publicznego API i odbieranie odpowiedzi,
* Rozpoznawanie w odpowiedzi kodu statusu, nagłówków i ciała (JSON),
* Diagnostyka HTTP z poziomu wiersza poleceń (`curl`),
* Korzystanie z interaktywnej dokumentacji API (Swagger),
* Poruszanie się po strukturze JSON:API: listy, obiekty, pola `data`, `attributes`, `links`,
* Pobranie realnego pliku danych z API i zapis wyników do JSON.

Narzędzia: Python (`requests`), `curl`, przeglądarka.

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

`curl` umożliwia zobaczenie dokładnie tego, co jest wysyłane i odbierane na poziomie protokołu HTTP — nagłówków, statusu, ciała odpowiedzi. 

## Przygotowanie

Sprawdź, czy masz `curl` (w terminalu / PowerShell):

~~~bash
curl --version
~~~

::: {.callout-warning}
## Uwaga dotycząca Windows
Jeśli pracujesz w PowerShell, wpisz `curl.exe` zamiast `curl`. Samo `curl` w PowerShell bywa aliasem do `Invoke-WebRequest` — zupełnie innego programu. Jeśli widzisz błąd wspominający o `Invoke-WebRequest`, to właśnie ten przypadek.
:::

## Nagłówki + ciało odpowiedzi

Flaga `-i` wyświetla **nagłówki odpowiedzi** razem z ciałem:

~~~bash
curl -i "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=2"
~~~

Na ekranie zobaczysz coś w rodzaju:

~~~
HTTP/2 200
content-type: application/vnd.api+json
...

{"data":[{"id":"...", ...}], ...}
~~~

::: {.callout-note}
Widzisz linię statusu (`HTTP/2 200`), nagłówki odpowiedzi (w tym `content-type`), pustą linię, a potem ciało odpowiedzi (JSON). To jest dokładnie struktura odpowiedzi HTTP z wykładu.
:::

## Tryb diagnostyczny

Flaga `-v` (verbose) pokazuje **też żądanie**, które wysłał twój klient:

~~~bash
curl -v "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=1"
~~~

W trybie `-v` `curl` oznacza różne typy linii prefiksami:

- Linie zaczynające się od `*` to **informacje diagnostyczne klienta** (np. rozwiązywanie DNS, TLS handshake).
- Linie zaczynające się od `>` to **żądanie** wysyłane przez ciebie (linia `GET ...` oraz nagłówki żądania).
- Linie zaczynające się od `<` to **odpowiedź serwera** (status i nagłówki odpowiedzi).

Uwaga: **ciało odpowiedzi** (np. JSON) pojawia się jako zwykły tekst bez prefiksów — jest wypisywane na standardowe wyjście, podczas gdy log `-v` idzie na standardowy błąd.

## Ćwiczenie: odczytywanie surowego HTTP

Wykonaj polecenie:

~~~bash
curl -v "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=1" 2>&1 | head -30
~~~

(`2>&1` łączy oba strumienie, żeby `head` mógł ograniczyć wyjście.)

Odpowiedz na pytania:

1. Jaka **metoda HTTP** została użyta? (szukaj w liniach `>`)
2. Jaki nagłówek **`Host`** wysłał twój klient?
3. Jaki **kod statusu** zwrócił serwer? (szukaj w liniach `<`)
4. Jaki **`content-type`** ma odpowiedź?


## HEAD — same nagłówki, bez ciała

Flaga `-I` wysyła żądanie `HEAD` — serwer zwraca **tylko nagłówki**, bez ciała odpowiedzi. Przydatne, gdy chcesz sprawdzić typ lub rozmiar zasobu przed jego pobraniem.

## Ćwiczenie: żądanie HEAD

Sprawdź to żądanie. Czy wszystko jest OK? 

~~~bash
curl -I "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=1"
~~~


## Ćwiczenie: HEAD vs GET

Wykonaj dwa polecenia i porównaj wyniki:

~~~bash
curl -I "https://httpbin.org/json"
curl -i "https://httpbin.org/json"
~~~

Odpowiedz:

1. Czy **kod statusu** jest taki sam w obu przypadkach?
2. Czy **`content-type`** jest taki sam?
3. Które polecenie **nie** zwróciło ciała odpowiedzi?
4. W jakiej sytuacji HEAD byłby przydatny?

## Formatowanie odpowiedzi JSON

`curl` wypisuje JSON w jednej linii — nieczytelnie. Pipe przez `python3 -m json.tool` formatuje z wcięciami:

~~~bash
curl -s "https://api.dane.gov.pl/1.4/datasets?page=1&per_page=2" | python3 -m json.tool | head -40
~~~

Flaga `-s` wycisza pasek postępu.

## Ćwiczenie: parametry zapytania i nagłówki

Wykonaj żądanie z parametrem wyszukiwania i nagłówkiem `Accept`:

~~~bash
curl -s -H "Accept: application/vnd.api+json" \
  "https://api.dane.gov.pl/1.4/datasets?q=transport&per_page=3" \
  | python3 -m json.tool | head -30
~~~

1. Ile datasetów zwrócił serwer? (policz obiekty w `data`)
2. Zmień frazę `transport` na inną (np. `szkoły`, `powietrze`). Czy wyniki się zmieniły?
3. Usuń flagę `-s` i wykonaj ponownie. Co się zmieniło w wyjściu?


---

# Zapytania HTTP w Pythonie (requests)

Od tego momentu pracujemy w Pythonie. Otwórz nowy notatnik Jupyter lub skrypt `.py` w Thonnym.

## Instalacja (jeśli potrzeba)

Biblioteka `requests` jest standardem do wysyłania zapytań HTTP w Pythonie, nie jest jednak częścią biblioteki standardowej, więc może wymagać instalacji:

```bash
pip install requests
```

## Obiekt Response — przypomnienie

Na wykładzie poznaliśmy bibliotekę `requests`. Wykonajmy jedno żądanie, żeby przypomnieć kluczowe atrybuty obiektu `Response`:

~~~python
import requests

r = requests.get("https://example.com", timeout=10)

print("Status:", r.status_code)        # int, np. 200
print("Content-Type:", r.headers.get("Content-Type"))
print("Treść (100 znaków):", r.text[:100])
~~~

Pełny zestaw atrybutów, z których będziemy korzystać:

* `r.status_code` — kod statusu (int),
* `r.headers` — słownik nagłówków odpowiedzi,
* `r.text` — ciało jako tekst (str),
* `r.content` — ciało jako bajty (bytes),
* `r.json()` — ciało sparsowane z JSON do dict/list,
* `r.url` — pełny URL po dołączeniu parametrów.

## httpbin.org — echo i symulacja błędów

[httpbin.org](https://httpbin.org/) to serwis testowy, który „odbija" twoje żądanie — pokazuje, co serwer otrzymał. Przydatny do nauki i debugowania.

**Echo żądania z parametrami i nagłówkami:**

~~~python
r = requests.get(
    "https://httpbin.org/get",
    params={"q": "python", "page": 1},
    headers={"Accept": "application/json", "User-Agent": "MojSkrypt/1.0"},
    timeout=10,
)

print("Pełny URL:", r.url)
echo = r.json()
print("Serwer widzi nagłówki:", echo["headers"])
print("Serwer widzi parametry:", echo["args"])
~~~

Zwróć uwagę: `requests` sam zakoduje parametry i doda `?...&...` do URL.

**Symulacja kodów błędów:**

httpbin potrafi zwrócić dowolny kod statusu — przydatne, żeby przetestować obsługę błędów bez czekania na „prawdziwy" błąd:

~~~python
for code in [200, 301, 404, 500]:
    r = requests.get(f"https://httpbin.org/status/{code}", allow_redirects=False, timeout=10)
    print(f"  Żądany kod: {code}, otrzymany: {r.status_code}")
~~~

::: {.callout-tip}
## Ważne
`r.json()` rzuci wyjątek, jeśli ciało odpowiedzi nie jest poprawnym JSON-em (np. gdy serwer zwrócił HTML ze stroną błędu). Dlatego przed parsowaniem warto sprawdzić `r.status_code` lub użyć `r.raise_for_status()`.
:::

## Bezpieczny wzorzec: sprawdzaj przed parsowaniem

~~~python
r = requests.get("https://httpbin.org/json", timeout=10)
r.raise_for_status()  # rzuci wyjątek przy 4xx / 5xx
data = r.json()
~~~

Metoda `raise_for_status()` zamienia kody błędów na wyjątek Pythona — dzięki temu nie próbujesz parsować odpowiedzi z błędem.

::: {.callout-note}
## Checkpoint
Wykonaj `requests.get("https://httpbin.org/status/418")`. Jaki kod statusu zwrócił serwer? Co się stanie, gdy na tym obiekcie wywołasz `raise_for_status()`?
:::

---

# Zapytanie do API dane.gov.pl

Teraz łączymy to, co wiemy o `requests`, ze strukturą API dane.gov.pl. Strategia: każdą odpowiedź zapisujemy do pliku JSON i otwieramy w edytorze lub przeglądarce. Dzięki temu widzisz pełną strukturę danych — zagnieżdżenia, klucze, typy — zamiast zgadywać z `print(data.keys())`.

## Przygotowanie: katalog i funkcja zapisu

Utwórz nowy skrypt (np. `lab1_api.py`). Na początku przygotuj katalog na odpowiedzi i pomocniczą funkcję:

```python
import json
import requests
from pathlib import Path

API = "https://api.dane.gov.pl/1.4"
OUT = Path("lab1_output")
OUT.mkdir(exist_ok=True)


def save_response(data, filename):
    """Zapisuje odpowiedź JSON do pliku i wypisuje ścieżkę."""
    path = OUT / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Zapisano: {path}")
```

To jest wzorzec z Lab 0 (`json.dumps` + `pathlib`) — teraz używamy go na żywych danych.

## Demonstracja: lista datasetów

Pobierz pierwszą stronę kolekcji i zapisz do pliku:

```python
r = requests.get(
    f"{API}/datasets",
    params={"page": 1, "per_page": 5},
    headers={"Accept": "application/vnd.api+json"},
    timeout=10,
)
r.raise_for_status()

save_response(r.json(), "datasets_page1.json")
```

Uruchom skrypt, a następnie **otwórz plik `lab1_output/datasets_page1.json`** w przeglądarce (Firefox i Chrome automatycznie formatują JSON).

## Co zobaczyć w pliku

Plik ma kilkaset linii. Nie czytaj go całego — szukaj struktury:

**Poziom główny** — trzy klucze:

* `"data"` — **lista** obiektów (datasetów). To główna zawartość odpowiedzi.
* `"links"` — adresy do nawigacji. Klucz `"next"` zawiera URL następnej strony wyników. To jest mechanizm **stronicowania**, którego użyjemy na Lab 2.
* `"meta"` — metadane. Klucz `"count"` mówi, ile jest datasetów łącznie (nie na tej stronie, lecz w całym API).

**Pojedynczy dataset** (element listy `"data"`) — zwróć uwagę na:

* `"id"` — identyfikator, którego użyjesz w kolejnym zapytaniu,
* `"type"` — zawsze `"dataset"`,
* `"attributes"` — słownik z właściwymi danymi: `"title"`, `"notes"`, `"category"`, `"modified"` itd.,
* `"links"` → `"self"` — URL tego konkretnego datasetu.

Zapisz sobie `id` jednego datasetu, który wydaje ci się ciekawy.


## Samodzielna eksploracja: element i podzasoby

Masz `id` wybranego datasetu. Teraz przejdź dwa kolejne poziomy hierarchii API — dokładnie te, które widziałeś w sekcji „Mapa zasobów API":

**1. Szczegóły datasetu** — endpoint `/datasets/{id}`

Pobierz szczegóły i zapisz do pliku (np. `dataset_{id}.json`). Otwórz plik i zwróć uwagę na kluczową różnicę: **`"data"` jest teraz słownikiem, nie listą**. Dla kolekcji API zwraca listę, dla pojedynczego elementu — obiekt.

**2. Zasoby datasetu** — endpoint `/datasets/{id}/resources`

Pobierz listę zasobów (plików) i zapisz do osobnego pliku. W każdym zasobie znajdź w `"attributes"` pola: `"title"`, `"format"`, `"download_url"`. Jeśli lista zasobów jest pusta — wybierz inny dataset i powtórz.

::: {.callout-tip}
## Wskazówka
Wzorzec kodu jest identyczny jak w demonstracji powyżej — zmienia się tylko URL i nazwa pliku wyjściowego. Użyj `save_response()`.
:::

**3. Podsumowanie na konsoli**

Gdy masz już zapisane pliki, wczytaj plik z zasobami i wypisz podsumowanie:

```python
resources = json.loads(
    (OUT / "resources_TWOJE_ID.json").read_text(encoding="utf-8")
)

for res in resources["data"]:
    attrs = res["attributes"]
    print(f"  [{res['id']}] {attrs.get('title', '(bez tytułu)')}")
    print(f"       format: {attrs.get('format', '?')}")
```

Ten fragment pokazuje ważny wzorzec: dane zapisane na dysk można wczytać i przetwarzać **bez ponownego odpytywania API**. To jest kluczowa umiejętność: **API → plik → analiza**. Dzięki temu nie obciążasz serwera wielokrotnymi zapytaniami, a jednocześnie masz 

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
* użyłeś `curl` do diagnostyki HTTP: nagłówki, kody statusu, HEAD vs GET,
* nauczyłeś się wysyłać zapytania GET w `requests` i parsować odpowiedzi JSON:API,
* przeszedłeś pełny łańcuch: kolekcja → element → podzasoby → pobranie pliku,
* zapisałeś wyniki do pliku JSON (pipeline: API → Python → plik),
* obsłużyłeś błędy HTTP (404, timeout).

W następnym labie: nawigacja po wielu stronach wyników (pętla po API), automatyczne pobieranie wielu plików i budowanie pipeline'u z obsługą retry.