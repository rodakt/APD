---
title: "Lab 6: Parsowanie HTML — XPath i lxml"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* XPath w praktyce: `//`, predykaty, osie, funkcje tekstowe i liczbowe,
* `lxml.etree` jako alternatywa dla BeautifulSoup,
* te same dane co w Lab 5 — teraz wyciągane XPath-em,
* zadania, których nie załatwisz selektorem CSS: selekcja po tekście, oś `following-sibling`, predykat arytmetyczny.

Narzędzia: Python (`lxml`, `requests`, Flask), VSCode.

---

# Przygotowanie

Serwery — te same co w Lab 5: serwer miast z Labu 4 oraz `bookshop`. Jeśli masz foldery z poprzednich labów, możesz je po prostu uruchomić.

Zainstaluj `lxml`:

```bash
pip install lxml
```

Sprawdź:

```bash
python -c "from lxml import etree; print('OK')"
```

Utwórz folder `lab6/` i otwórz go w VSCode.

::: {.callout-tip}
## Instalacja pakietów w pracowni
Komputery w pracowni mogą resetować pakiety między sesjami. Na początku każdego labu sprawdź, czy `lxml` i `flask` są dostępne, i w razie potrzeby zainstaluj ponownie.
:::

---

# Szybka ściąga XPath

Poniżej minimum, które wystarczy na wszystkie zadania z tego labu. Pełna składnia — w Wykładzie 3.

## Ścieżki

| Wyrażenie | Znaczenie |
|---|---|
| `//tag` | wszystkie `<tag>` w całym dokumencie |
| `//table//tr` | `<tr>` wewnątrz `<table>` (dowolna głębokość) |
| `//table/tr` | `<tr>` będące bezpośrednim dzieckiem `<table>` |
| `td[1]/text()` | ścieżka względna — liczona od bieżącego węzła |

## Predykaty (`[...]`)

| Wyrażenie | Znaczenie |
|---|---|
| `//td[@class="price"]` | `<td>` z `class="price"` |
| `//a[@href]` | `<a>` z dowolnym atrybutem `href` |
| `//td[contains(@class,"price")]` | klasa zawiera „price" |
| `//tr[1]` / `//tr[last()]` | pierwszy / ostatni `<tr>` (numerowanie od 1) |
| `//tr[position()>1]` | wszystkie `<tr>` oprócz pierwszego |
| `//a[text()="Dalej"]` | dokładny tekst |
| `//a[contains(text(),"Dalej")]` | tekst zawiera „Dalej" |
| `//tr[number(td[2]/text()) > 500000]` | predykat arytmetyczny |

## Wyciąganie danych

| Wyrażenie | Zwraca |
|---|---|
| `//td` | listę elementów `<td>` |
| `//td/text()` | listę stringów — tekst każdej komórki |
| `//a/@href` | listę wartości atrybutu `href` |
| `el.text` / `el.get("class")` | pojedyncza wartość (jak w bs4) |

## Osie

| Wyrażenie | Znaczenie |
|---|---|
| `//td[text()="X"]/..` | rodzic (skrót od `parent::node()`) |
| `//td[text()="X"]/following-sibling::td[1]` | następna komórka obok |
| `//td[text()="X"]/preceding-sibling::td[1]` | poprzednia komórka obok |
| `//td[@class="price"]/ancestor::table` | przodek typu `<table>` |

## Relatywne vs absolutne

`.xpath(...)` można wywołać na dowolnym węźle. Wyrażenia bez `//` są wtedy **względne** do tego węzła:

```python
row = tree.xpath('//tr[2]')[0]
row.xpath('td[1]/text()')    # pierwsze <td> TEGO wiersza
row.xpath('.//a/@href')      # wszystkie <a> wewnątrz tego wiersza
```

Uwaga: `//a` wywołane na węźle wciąż oznacza „gdziekolwiek w dokumencie". Dla „gdziekolwiek wewnątrz tego węzła" używaj `.//`.

---

# Demonstracja: crawler miast w XPath

Ten sam crawler co w Demonstracji z Labu 5 — tym razem z `lxml` i XPath. Serwer, pętla `while`, `requests.get` i zapis do JSON zostają bez zmian.

Uruchom serwer miast (Lab 4/5) w **Terminalu 1**:

```bash
flask run --debug -p 5000
```

Utwórz `crawler_xpath.py` w **Terminalu 2**:

```python
import json
import requests
from lxml import etree

BASE = "http://127.0.0.1:5000"


def crawl_catalog(start_url):
    all_cities = []
    url = start_url

    while url is not None:
        r = requests.get(url)
        r.raise_for_status()
        tree = etree.HTML(r.text)

        # --- Ekstrakcja ---
        rows = tree.xpath('//table//tr[position()>1]')   # pomijamy nagłówek
        for row in rows:
            all_cities.append({
                "name": row.xpath('td[1]/text()')[0],
                "population": int(row.xpath('td[2]/text()')[0]),
                "voivodeship": row.xpath('td[3]/text()')[0],
            })

        # --- Nawigacja ---
        hrefs = tree.xpath('//a[contains(text(),"Następna")]/@href')
        url = BASE + hrefs[0] if hrefs else None

        print(f"Pobrano stronę, łącznie miast: {len(all_cities)}")

    return all_cities


cities = crawl_catalog(f"{BASE}/catalog?page=1")
print(f"\nZebrano {len(cities)} miast.")

with open("cities.json", "w", encoding="utf-8") as f:
    json.dump(cities, f, ensure_ascii=False, indent=2)
```

Uruchom i porównaj wynik z plikiem `cities.json` z Labu 5 — powinien być identyczny.

Dwie rzeczy warte odnotowania:

* `tr[position()>1]` — pomijamy nagłówek **w wyrażeniu XPath**, nie przez `[1:]` po stronie Pythona.
* Nawigacja po tekście linku (`contains(text(),"Następna")`) — zamiast klasy `.next-page`. Działałoby nawet, gdyby link nie miał żadnej klasy.

::: {.callout-note}
## Checkpoint
1. Czy crawler zebrał 30 miast?
2. Otwórz `cities.json` i porównaj z plikiem z Labu 5 — czy zawartość jest taka sama?
3. Policz linijki parsowania (od `tree = ...` do przypisania `url`). Porównaj z wersją BeautifulSoup.
:::

---

# Ćwiczenie 1: bookshop — listing i strona detali

Port `bookshop_css.py` z Labu 5 na XPath. Zatrzymaj serwer miast (`Ctrl+C`) i uruchom `bookshop`:

```bash
cd bookshop
flask run --debug -p 5000
```

Utwórz `bookshop_xpath.py`:

```python
import requests
from lxml import etree

BASE = "http://127.0.0.1:5000"

# --- Część A: listing ---

r = requests.get(f"{BASE}/books")
r.raise_for_status()
tree = etree.HTML(r.text)

books = []

# 1. Znajdź wszystkie elementy książek (klasa "book").
for book_el in tree.xpath('...'):                       # <- uzupełnij
    # 2. Wyciągnij tytuł, autora, cenę i URL strony detali.
    #    Ścieżka jest względna do book_el.
    #    Tekst: .../text() ; atrybut: .../@href
    title = book_el.xpath('...')[0]                     # <- uzupełnij
    author = book_el.xpath('...')[0]                    # <- uzupełnij
    price = book_el.xpath('...')[0]                     # <- uzupełnij
    detail_url = BASE + book_el.xpath('...')[0]         # <- uzupełnij

    books.append({
        "title": title,
        "author": author,
        "price": price,
        "detail_url": detail_url,
    })

for b in books:
    print(f"  {b['title']} — {b['author']} — {b['price']}")


# --- Część B: strona detali ---

# 3. Pobierz stronę detali pierwszej książki.
#    Wyciągnij: tytuł (h1.title), autora, opis (klasa "description"),
#    cenę i stan magazynowy (klasa "stock").
#    Użyj XPath na nowym drzewie.
# --- Twój kod ---

print(f"\nSzczegóły: {title}")
print(f"  Autor: {author}")
print(f"  Cena: {price}")
print(f"  Opis: {description[:80]}...")
print(f"  Magazyn: {stock}")
```

::: {.callout-tip}
## `xpath(...)[0]` i lista jednoelementowa
XPath zawsze zwraca listę — nawet gdy wynik jest jeden. `[0]` bierze pierwszy element. Jeśli lista jest pusta (element nie istnieje), dostaniesz `IndexError` — to prostszy i bardziej wykrywalny błąd niż `None` z `find()`.
:::

::: {.callout-note}
## Checkpoint
1. Czy Część A wypisuje 5 książek?
2. Czy Część B poprawnie wyciąga opis i stan magazynowy?
3. Czy `detail_url` to pełny URL, nie sama ścieżka?
:::

---

# Ćwiczenie 2: dziesięć zapytań XPath

Jeden plik, jedna strona (listing bookshop), dziesięć niezależnych zapytań od najłatwiejszych do najtrudniejszych. Każde zadanie to jedna linia komentarza + miejsce na wyrażenie. Stronę pobierasz raz, na górze pliku.

Utwórz `bookshop_queries.py`:

```python
import requests
from lxml import etree

BASE = "http://127.0.0.1:5000"
listing = etree.HTML(requests.get(f"{BASE}/books").text)


# === Rozgrzewka ===

# 1. Tytuły wszystkich książek.
print(listing.xpath('...'))

# 2. Wszystkie wartości atrybutu href na stronie.
print(listing.xpath('...'))

# 3. Liczba książek na stronie.
print(len(listing.xpath('...')))


# === Osie i tekst ===

# 4. Href linku do następnej strony — po tekście linku, nie po klasie.
print(listing.xpath('...'))

# 5. Cena książki "Pan Tadeusz" — przechodząc osią od jej tytułu.
print(listing.xpath('...'))

# 6. URL detali "Pana Tadeusza" — również osią.
print(listing.xpath('...'))

# 7. Słownik {tytuł: cena} dla wszystkich książek.
prices = {}
for book in listing.xpath('...'):
    title = book.xpath('...')[0]
    price = book.xpath('...')[0]
    prices[title] = price
print(prices)


# === Predykaty i funkcje ===

# 8. Tytuły książek, których autor ma w nazwisku "icz".
print(listing.xpath('...'))

# 9. Tytuły książek tańszych niż 30 zł.
#    Ceny są w formacie "34,90 zł" — w jednym wyrażeniu XPath potrzebujesz:
#      substring-before(..., " zł")   — odcina jednostkę,
#      translate(..., ",", ".")       — zamienia przecinek na kropkę,
#      number(...)                    — parsuje jako liczbę.
print(listing.xpath('...'))


# === Granica XPath ===

# 10. Tytuł najdroższej książki na stronie.
#     XPath 1.0 nie ma funkcji max — wyciągnij pary (tytuł, cena) i znajdź
#     maksimum Pythonem.
# --- Twój kod ---
```

::: {.callout-note}
## Checkpoint
1. Zadania 1–3: pięć tytułów, siedem wartości `href`, pięć książek.
2. Zadania 5–6: dla „Pana Tadeusza" cena to `22,00 zł`, a URL detali to `/book/3`.
3. Zadanie 8: wynik to dokładnie „Ferdydurke" i „Pan Tadeusz".
4. Zadanie 9: ten sam wynik co zadanie 8, ale z zupełnie innego powodu.
5. Zadanie 10: „Chłopi" (44,90 zł).
:::

---

# Ćwiczenie 3: pełny crawl bookshop w XPath

Odpowiednik Ćwiczenia 3 z Lab 5 — teraz wyłącznie w XPath. Masz już `bookshop.json` z Labu 5 jako punkt odniesienia.

## Wymagania

1. Start: `http://127.0.0.1:5000/books`.
2. Na każdej stronie listingu: wyciągnij tytuł, autora, cenę, URL detali każdej książki. Znajdź link do następnej strony (klasa `next-page`) — jeśli go nie ma, koniec.
3. Dla każdej książki wejdź na stronę detali, dociągnij opis i stan magazynowy.
4. Zapisz wszystko do `bookshop_xpath.json`.

## Szkielet

```python
import json
import requests
from lxml import etree

BASE = "http://127.0.0.1:5000"


def get_book_detail(url):
    """Zwraca (opis, stan_magazynowy) ze strony detali."""
    # --- Twój kod ---
    pass


def crawl_bookshop(start_url):
    all_books = []
    url = start_url

    while url is not None:
        r = requests.get(url)
        r.raise_for_status()
        tree = etree.HTML(r.text)

        # 1. Wyciągnij książki z bieżącej strony (jak w Ćw. 1, Część A).
        # --- Twój kod ---

        # 2. Dla każdej książki dociągnij detale (get_book_detail).
        # --- Twój kod ---

        # 3. Link do następnej strony.
        #    Wskazówka: //a[@class="next-page"]/@href
        #    Uwaga: xpath() zwraca listę — sprawdź, czy jest niepusta.
        # --- Twój kod ---

        print(f"Strona pobrana, łącznie książek: {len(all_books)}")

    return all_books


books = crawl_bookshop(f"{BASE}/books")
print(f"\nZebrano {len(books)} książek.")

with open("bookshop_xpath.json", "w", encoding="utf-8") as f:
    json.dump(books, f, ensure_ascii=False, indent=2)
```

::: {.callout-tip}
## Porównanie z Labem 5
Po zakończeniu sprawdź: `bookshop_xpath.json` i `bookshop.json` (Lab 5) powinny zawierać te same dane. Jeśli nie — masz żywą regresję: różne narzędzia, ta sama strona, różny wynik → gdzieś jest błąd w ekstrakcji.
:::

::: {.callout-note}
## Checkpoint
1. Ile książek zebrał crawler? Czy zgadza się z liczbą z Labu 5?
2. Czy każda książka ma wszystkie pola (tytuł, autor, cena, opis, stan)?
3. Czy crawler zatrzymał się na ostatniej stronie (nie zapętlił się)?
:::

---

# Ćwiczenie 4 (dodatkowe): Hacker News — osie w akcji

Struktura Hacker News (`https://news.ycombinator.com`) jest specyficzna: każdy wpis to **para wierszy** tabeli.

* `<tr class="athing">` — tytuł i link,
* następny `<tr>` (bez klasy) — metadane: punkty, autor, komentarze.

W Labie 5 obejście tego wymagało iteracji po rodzeństwie przez bs4 (`find_next_sibling`) albo parowania `zip`. W XPath — jedna oś:

```python
row.xpath('following-sibling::tr[1]')   # następny wiersz
```

## Zadanie

Napisz `hackernews_xpath.py`. Pobierz stronę główną (jedno żądanie) i wyciągnij listę wpisów — dla każdego: tytuł, URL, liczba punktów, liczba komentarzy. Zapisz do `hackernews.json`.

```python
import json, re
import requests
from lxml import etree

r = requests.get("https://news.ycombinator.com")
r.raise_for_status()
tree = etree.HTML(r.text)

items = []

# 1. Wiersze tytułowe.
for row in tree.xpath('//tr[@class="athing"]'):
    # 2. Tytuł i URL — w row, w .titleline > a.
    #    Uwaga: relatywny XPath z .// (szukamy wewnątrz row).
    # --- Twój kod ---

    # 3. Wiersz metadanych — following-sibling::tr[1].
    # --- Twój kod ---

    # 4. Z metadanych wyciągnij:
    #      - punkty ze .score, np. "153 points" -> 153
    #        (uwaga: nie każdy wpis ma .score — zabezpiecz się)
    #      - liczbę komentarzy z ostatniego <a>, np. "87 comments" -> 87
    #        (uwaga: wpisy bez komentarzy mają tekst "discuss")
    # --- Twój kod ---

    items.append({...})

with open("hackernews.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Zebrano {len(items)} wpisów.")
```

::: {.callout-note}
## Checkpoint
1. Czy zebrałeś ~30 wpisów?
2. Czy punkty i komentarze to `int`, nie stringi?
3. Porównaj kod z rozwiązaniem tego samego zadania w Labie 5 (jeśli je robiłeś). Który fragment był wyraźnie krótszy dzięki `following-sibling`?
:::

---

# Podsumowanie

W tym labie:

* ten sam crawler miast i bookshop co w Labie 5 — teraz w XPath i `lxml`,
* predykaty pozycyjne (`[position()>1]`, `[last()]`) i tekstowe (`contains(text(),...)`),
* osie — w szczególności `following-sibling` jako naturalny sposób na „komórka obok",
* predykat arytmetyczny (`number(...) > X`) — filtrowanie, którego CSS nie zrobi,
* relatywne XPath (`td[1]/text()`, `.//a`) — wyrażenie względne do węzła, na którym wywołasz `.xpath(...)`.

**Co dalej:**

* **Wykład 4**: cookies, sesje, formularze HTML — serwer „pamięta" klienta.
* **Lab 7**: budujemy serwer Flask z logowaniem i formularzem.
