---
title: "Lab 4: Paginacja HTML i prosty crawler"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Budowa serwera Flask z paginacją HTML (strony z linkami „Następna" / „Poprzednia"),
* Wyciąganie linków i danych z HTML za pomocą wyrażeń regularnych (`re`),
* Pisanie crawlera: pętla pobierająca kolejne strony katalogu i zbierająca dane,
* Zapis zebranych danych do pliku JSON.

Narzędzia: Python (Flask, `requests`, `re`, `json`), VSCode.

---

# Przygotowanie

Środowisko pracy jest takie samo jak na Labie 3: VSCode, dwa terminale (serwer + klient), Flask.

Sprawdź, czy Flask jest dostępny:

```bash
pip install flask
```

Utwórz nowy folder roboczy (np. `lab4/`) i otwórz go w VSCode.

Na tym labie używamy dodatkowo modułu `re` (wyrażenia regularne) — jest częścią biblioteki standardowej Pythona, nie wymaga instalacji.

---

# Demonstracja 1: serwer z paginacją HTML

Na Labie 2 przechodziliśmy po stronach wyników API dane.gov.pl — każda odpowiedź JSON zawierała pole `links.next` z adresem następnej strony. Większość stron w internecie nie ma publicznego API — dzielą wyniki na podstrony HTML z linkami nawigacyjnymi („Następna", „Poprzednia").

Utwórz plik `app.py`:

```python
from flask import Flask, request

app = Flask(__name__)

CITIES = [
    {"name": "Warszawa", "population": 1_862_000, "voivodeship": "mazowieckie"},
    {"name": "Kraków", "population": 804_000, "voivodeship": "małopolskie"},
    {"name": "Łódź", "population": 672_000, "voivodeship": "łódzkie"},
    {"name": "Wrocław", "population": 674_000, "voivodeship": "dolnośląskie"},
    {"name": "Poznań", "population": 546_000, "voivodeship": "wielkopolskie"},
    {"name": "Gdańsk", "population": 486_000, "voivodeship": "pomorskie"},
    {"name": "Szczecin", "population": 398_000, "voivodeship": "zachodniopomorskie"},
    {"name": "Bydgoszcz", "population": 348_000, "voivodeship": "kujawsko-pomorskie"},
    {"name": "Lublin", "population": 340_000, "voivodeship": "lubelskie"},
    {"name": "Białystok", "population": 298_000, "voivodeship": "podlaskie"},
    {"name": "Katowice", "population": 292_000, "voivodeship": "śląskie"},
    {"name": "Gdynia", "population": 246_000, "voivodeship": "pomorskie"},
    {"name": "Częstochowa", "population": 224_000, "voivodeship": "śląskie"},
    {"name": "Radom", "population": 214_000, "voivodeship": "mazowieckie"},
    {"name": "Toruń", "population": 198_000, "voivodeship": "kujawsko-pomorskie"},
    {"name": "Sosnowiec", "population": 196_000, "voivodeship": "śląskie"},
    {"name": "Rzeszów", "population": 196_000, "voivodeship": "podkarpackie"},
    {"name": "Kielce", "population": 195_000, "voivodeship": "świętokrzyskie"},
    {"name": "Gliwice", "population": 179_000, "voivodeship": "śląskie"},
    {"name": "Olsztyn", "population": 172_000, "voivodeship": "warmińsko-mazurskie"},
    {"name": "Zabrze", "population": 172_000, "voivodeship": "śląskie"},
    {"name": "Bielsko-Biała", "population": 171_000, "voivodeship": "śląskie"},
    {"name": "Bytom", "population": 163_000, "voivodeship": "śląskie"},
    {"name": "Zielona Góra", "population": 142_000, "voivodeship": "lubuskie"},
    {"name": "Rybnik", "population": 139_000, "voivodeship": "śląskie"},
    {"name": "Ruda Śląska", "population": 138_000, "voivodeship": "śląskie"},
    {"name": "Opole", "population": 128_000, "voivodeship": "opolskie"},
    {"name": "Tychy", "population": 128_000, "voivodeship": "śląskie"},
    {"name": "Gorzów Wielkopolski", "population": 124_000, "voivodeship": "lubuskie"},
    {"name": "Elbląg", "population": 120_000, "voivodeship": "warmińsko-mazurskie"},
]

PER_PAGE = 10


@app.route("/")
def index():
    return """
    <html><body>
        <h1>Miasta Polski</h1>
        <p>Serwer z paginacją HTML — Lab 4</p>
        <a href="/catalog?page=1">Przejdź do katalogu</a>
    </body></html>
    """


@app.route("/catalog")
def catalog():
    page = request.args.get("page", 1, type=int)
    total_pages = (len(CITIES) + PER_PAGE - 1) // PER_PAGE

    if page < 1 or page > total_pages:
        return "<html><body><h1>404</h1><p>Nie ma takiej strony.</p></body></html>", 404

    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_cities = CITIES[start:end]

    # Nagłówek
    html = f"""
    <html><body>
    <h1>Katalog miast — strona {page} z {total_pages}</h1>
    <table border="1">
        <tr><th>Nazwa</th><th>Populacja</th><th>Województwo</th></tr>
    """

    # Wiersze tabeli
    for city in page_cities:
        html += f"""
        <tr>
            <td>{city['name']}</td>
            <td>{city['population']}</td>
            <td>{city['voivodeship']}</td>
        </tr>"""

    html += "\n    </table>\n    <p>"

    # Linki nawigacyjne
    if page > 1:
        html += f'<a href="/catalog?page={page - 1}">← Poprzednia</a> '
    if page < total_pages:
        html += f'<a href="/catalog?page={page + 1}">Następna →</a>'

    html += "</p>\n    </body></html>"
    return html
```

Uruchom serwer w **Terminalu 1**:

```bash
flask run --debug -p 5000
```

Otwórz `http://localhost:5000/catalog?page=1` w przeglądarce. Przejdź po stronach klikając „Następna →".

::: {.callout-note}
## Checkpoint
Otwórz `/catalog?page=3`. Czy widzisz 10 miast? Czy link „Następna →" zniknął (bo to ostatnia strona)? Czy „← Poprzednia" prowadzi do strony 2?
:::

## Porównanie z paginacją API

Na Labie 2 paginacja wyglądała tak:

```python
data = r.json()
next_url = data["links"]["next"]   # czyste, strukturalne
```

Tutaj dane i nawigacja są zakopane w HTML. Żeby wyciągnąć link do następnej strony, trzeba **przeszukać tekst HTML**. Wykorzystamy do tego wyrażenia regularne.

---

# Demonstracja 2: wyciąganie danych z HTML

Serwer z Demonstracji 1 działa. W **Terminalu 2** otwórz interaktywny Python (`python`) lub utwórz skrypt `crawler.py`.

## Krok 1: pobranie strony

```python
import requests

r = requests.get("http://localhost:5000/catalog?page=1")
html = r.text
print(html)
```

Widzisz surowy HTML — tabela z miastami i linki nawigacyjne.

## Krok 2: link do następnej strony

```python
import re

match = re.search(r'<a href="([^"]+)">Następna', html)
if match:
    next_path = match.group(1)
    print("Następna strona:", next_path)
else:
    print("Brak następnej strony")
```

::: {.callout-tip}
## Wyrażenie regularne — co robi ten wzorzec?
`<a href="([^"]+)">Następna` — szuka tekstu `<a href="`, potem **przechwytuje** (nawiasy) ciąg znaków niebędących cudzysłowem `[^"]+`, potem zamykający `"` i tekst `Następna`. Wynik w `match.group(1)` to wartość atrybutu `href`.
:::

Zwróć uwagę: `next_path` to ścieżka względna (np. `/catalog?page=2`), nie pełny URL. Aby użyć jej w `requests.get`, trzeba dodać adres serwera:

```python
base = "http://localhost:5000"
next_url = base + next_path
print(next_url)
```

## Krok 3: dane z tabeli

```python
rows = re.findall(
    r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>",
    html,
)
for name, population, voivodeship in rows:
    print(f"{name:20s} {population:>10s}  {voivodeship}")
```

::: {.callout-tip}
## Wyrażenie regularne — co robi ten wzorzec?
`<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>` — szuka wiersza tabeli (`<tr>...</tr>`) z trzema komórkami (`<td>...</td>`). Każde `(.*?)` przechwytuje zawartość jednej komórki. `\s*` ignoruje białe znaki (spacje, nowe linie) między tagami. `re.findall` zwraca listę krotek — po jednej na każdy wiersz.
:::

::: {.callout-warning}
## Regex na HTML jest zawodny
Ten wzorzec zadziała, bo HTML naszego serwera ma przewidywalny format. Gdyby tabela miała dodatkowe atrybuty (`<td class="...">`), zagnieżdżone tagi albo inny układ spacji — regex by się załamał. Lepszego rozwiązania dostarczają biblioteki do parsowania HTML, np. BeautifulSoup.
:::

::: {.callout-note}
## Checkpoint
Czy `rows` ma 10 elementów (tyle miast na stronie)? Czy `population` to string (np. `"1862000"`)? Pamiętaj, że regex zawsze zwraca tekst — konwersja na `int` to osobny krok.
:::

---

# Ćwiczenie 1: crawler katalogu miast

Serwer z Demonstracji 1 nadal działa. Na Demonstracji 2 zobaczyłeś, jak pobrać jedną stronę i wyciągnąć z niej dane oraz link do następnej. Teraz zamknij ten mechanizm w pętli.

Utwórz plik `crawler.py` i uzupełnij szkielet:

```python
import re
import json
import requests

BASE = "http://localhost:5000"

# Wzorce regex — użyj ich w kodzie poniżej.
NEXT_LINK_PATTERN = r'<a href="([^"]+)">Następna'
ROW_PATTERN = r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>"


def crawl_catalog(start_url):
    """Przechodzi po stronach katalogu, zbiera dane o miastach.

    Parameters
    ----------
    start_url : str
        URL pierwszej strony, np. "http://localhost:5000/catalog?page=1".

    Returns
    -------
    list[dict]
        Lista słowników z kluczami: name, population, voivodeship.
    """
    all_cities = []
    url = start_url
    page_num = 0

    while url is not None:
        page_num += 1

        # 1. Pobierz stronę. Użyj requests.get() i raise_for_status().
        # --- Twój kod ---

        # 2. Wyciągnij wiersze z tabeli (re.findall + ROW_PATTERN).
        #    Dla każdego wiersza utwórz słownik
        #    {"name": ..., "population": int(...), "voivodeship": ...}
        #    i dodaj do all_cities.
        # --- Twój kod ---

        # 3. Znajdź link do następnej strony (re.search + NEXT_LINK_PATTERN).
        #    Jeśli jest — zbuduj pełny URL (BASE + ścieżka).
        #    Jeśli brak — ustaw url = None.
        # --- Twój kod ---

        # 4. Wypisz postęp, np.: "Strona 1: pobrano 10 miast (łącznie 10)"
        # --- Twój kod ---

    return all_cities


cities = crawl_catalog(f"{BASE}/catalog?page=1")
print(f"\nZebrano {len(cities)} miast.")

# Zapis do pliku
with open("cities.json", "w", encoding="utf-8") as f:
    json.dump(cities, f, ensure_ascii=False, indent=2)

print("Zapisano do cities.json")
```

Przetestuj:

```python
import requests

r = requests.get("http://localhost:5000/catalog?page=1")
print(r.text[:500])   # podgląd HTML — czy wygląda jak oczekiwany?
```

::: {.callout-note}
## Checkpoint

1. Czy crawler wypisał 3 strony i zebrał 30 miast?
2. Czy plik `cities.json` zawiera poprawne dane? Otwórz go i sprawdź.
3. Czy crawler zatrzymał się sam na ostatniej stronie (nie zapętlił się)?
4. Czy wartości `population` to liczby (`int`), nie stringi?
:::

---

# Ćwiczenie 2: własny serwer paginowany

Teraz zbuduj serwer z paginacją od podstaw — z innym zestawem danych. Poniżej szkielet serwera z listą polskich gór. Uzupełnij trasę `/peaks`.

Utwórz nowy plik `app.py` (zatrzymaj poprzedni serwer przez `Ctrl+C`):

```python
from flask import Flask, request

app = Flask(__name__)

PEAKS = [
    {"name": "Rysy", "height": 2499, "range": "Tatry"},
    {"name": "Świnica", "height": 2301, "range": "Tatry"},
    {"name": "Kasprowy Wierch", "height": 1987, "range": "Tatry"},
    {"name": "Giewont", "height": 1895, "range": "Tatry"},
    {"name": "Turbacz", "height": 1310, "range": "Gorce"},
    {"name": "Babia Góra", "height": 1725, "range": "Beskid Żywiecki"},
    {"name": "Pilsko", "height": 1557, "range": "Beskid Żywiecki"},
    {"name": "Tarnica", "height": 1346, "range": "Bieszczady"},
    {"name": "Halicz", "height": 1333, "range": "Bieszczady"},
    {"name": "Śnieżka", "height": 1603, "range": "Karkonosze"},
    {"name": "Wielki Szyszak", "height": 1509, "range": "Karkonosze"},
    {"name": "Śnieżnik", "height": 1425, "range": "Masyw Śnieżnika"},
    {"name": "Lackowa", "height": 997, "range": "Beskid Niski"},
    {"name": "Mogielica", "height": 1170, "range": "Beskid Wyspowy"},
    {"name": "Luboń Wielki", "height": 1022, "range": "Beskid Wyspowy"},
    {"name": "Skrzyczne", "height": 1257, "range": "Beskid Śląski"},
    {"name": "Barania Góra", "height": 1220, "range": "Beskid Śląski"},
    {"name": "Wielka Rawka", "height": 1307, "range": "Bieszczady"},
    {"name": "Połonina Caryńska", "height": 1297, "range": "Bieszczady"},
    {"name": "Szczeliniec Wielki", "height": 919, "range": "Góry Stołowe"},
]

PER_PAGE = 5


@app.route("/")
def index():
    return """
    <html><body>
        <h1>Szczyty Polski</h1>
        <a href="/peaks?page=1">Katalog szczytów</a>
    </body></html>
    """


@app.route("/peaks")
def peaks():
    page = request.args.get("page", 1, type=int)

    # 1. Oblicz total_pages — ile stron potrzeba, żeby wyświetlić
    #    wszystkie szczyty po PER_PAGE na stronę.
    #    Wskazówka: (len(PEAKS) + PER_PAGE - 1) // PER_PAGE
    # --- Twój kod ---

    # 2. Walidacja: jeśli page < 1 lub page > total_pages,
    #    zwróć HTML z komunikatem "Nie ma takiej strony." i kod 404.
    # --- Twój kod ---

    # 3. Oblicz start i end — indeksy wycinka listy PEAKS
    #    dla bieżącej strony. Wyciągnij page_peaks = PEAKS[start:end].
    # --- Twój kod ---

    # 4. Zbuduj string HTML:
    #    - nagłówek <h1> z numerem strony i liczbą stron,
    #    - tabela <table border="1"> z nagłówkami: Nazwa, Wysokość, Pasmo,
    #    - wiersz <tr><td>...</td>... dla każdego szczytu,
    #    - linki nawigacyjne:
    #        * "← Poprzednia" (jeśli page > 1),
    #        * "Następna →" (jeśli page < total_pages).
    #
    #    WAŻNE: format linków musi być dokładnie taki:
    #        <a href="/peaks?page=N">Następna →</a>
    #        <a href="/peaks?page=N">← Poprzednia</a>
    #    Dzięki temu crawler z Ćwiczenia 1 będzie działał
    #    na tym serwerze po minimalnych zmianach.
    # --- Twój kod ---

    return html
```

Uruchom serwer i przetestuj w przeglądarce.

::: {.callout-note}
## Checkpoint

1. Czy `/peaks?page=1` wyświetla 5 szczytów? Czy strona 4 wyświetla ostatnie 5?
2. Czy na stronie 1 nie ma linku „← Poprzednia"? Czy na ostatniej stronie nie ma „Następna →"?
3. **Test crawlerem**: zmodyfikuj `crawl_catalog` z Ćwiczenia 1 — zmień `start_url` na `http://localhost:5000/peaks?page=1` i dostosuj klucze słownika (`name`, `height`, `range`). Czy crawler przechodzi po wszystkich stronach i zbiera 20 szczytów?
:::

---

# Ćwiczenia samodzielne

## Ćwiczenie A: crawler na serwer Collatza

Na Wykładzie 2 widzieliśmy serwer generujący strony HTML dla ciągu Collatza — każda strona to liczba, a link prowadzi do następnej w ciągu. Uruchom ten serwer (kod z Wykładu 2) i napisz crawlera, który:

1. Startuje od `/collatz/27`.
2. Pobiera stronę, wyciąga link do następnej liczby.
3. Zbiera odwiedzone liczby do listy.
4. Zatrzymuje się, gdy dotrze do `n = 1`.
5. Wypisuje cały ciąg i zapisuje go do pliku `collatz_27.json`.

::: {.callout-tip}
## Wskazówka: wyciąganie linku
Link na stronie Collatza ma postać `<a href="/collatz/N">Przejdź do N</a>`. Użyj wzorca `r'<a href="(/collatz/\d+)">Przejdź'` — `\d+` oznacza jedną lub więcej cyfr.
:::

Porównaj z Ćwiczeniem 1: tam crawler przechodził po stronach katalogu (wiele danych na stronie, link „Następna"). Tu przechodzi po ciągu liczbowym (jedna dana na stronie, link do konkretnej następnej). Wzorzec jest ten sam: pobierz stronę → wyciągnij link → podążaj.

## Ćwiczenie B: konfigurowalny `per_page`

Rozbuduj serwer z Ćwiczenia 2 tak, aby `per_page` było parametrem query string:

* `/peaks?page=1&per_page=3` — 3 szczyty na stronę (7 stron),
* `/peaks?page=1&per_page=10` — 10 szczytów na stronę (2 strony),
* `/peaks?page=1` — domyślnie 5 na stronę (jak dotychczas).

Przetestuj crawlerem: zbierz dane raz z `per_page=3`, raz z `per_page=10`. Czy w obu przypadkach wynik to te same 20 szczytów?

::: {.callout-tip}
## Wskazówka
Użyj `request.args.get("per_page", PER_PAGE, type=int)`. Pamiętaj, żeby linki nawigacyjne zawierały parametr `per_page`, np. `/peaks?page=2&per_page=3` — inaczej po kliknięciu „Następna" serwer wróci do domyślnej wartości.
:::

## Ćwiczenie C (dodatkowe): serwer z losowymi błędami + retry

Rozbuduj serwer z Ćwiczenia 2: z prawdopodobieństwem 30% zwracaj kod 503 zamiast normalnej odpowiedzi.

```python
import random

@app.route("/peaks")
def peaks():
    if random.random() < 0.3:
        return "<html><body><h1>503</h1><p>Serwer przeciążony</p></body></html>", 503
    # ... reszta kodu ...
```

Rozbuduj crawlera o prostą logikę retry: jeśli dostaniesz 503, poczekaj sekundę i spróbuj ponownie (maks. 3 próby).

::: {.callout-tip}
## Wskazówka
Na Labie 2 napisałeś funkcję `fetch_with_retry`. Możesz ją tu wykorzystać bez zmian — wystarczy zaimportować lub skopiować.
:::

---

# Podsumowanie

W tym labie:

* uruchomiłeś serwer z paginacją HTML — odpowiednik stron, które dzielą wyniki na podstrony z linkami „Następna / Poprzednia",
* napisałeś crawlera, który automatycznie przechodzi po stronach i zbiera dane — pętla: pobierz → wyciągnij link → podążaj,
* użyłeś wyrażeń regularnych do wyciągania linków i danych z HTML — i zobaczyłeś, jak kruche i niewygodne jest parsowanie HTML w ten sposób,
* zbudowałeś własny serwer paginowany i przetestowałeś na nim crawlera z innym zestawem danych.

**Co dalej:**

* **Wykład 3**: HTML jako drzewo — BeautifulSoup, selektory CSS, XPath. Koniec z wyrażeniami regularnymi na HTML.
* **Laby 5–6**: ekstrakcja danych z HTML za pomocą dedykowanych narzędzi.