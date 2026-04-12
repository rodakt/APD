---
title: "Lab 5: Parsowanie HTML — BeautifulSoup i selektory CSS"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Parsowanie HTML za pomocą BeautifulSoup — przejście z wyrażeń regularnych na parser rozumiejący strukturę dokumentu,
* Wyszukiwanie elementów: `find`, `find_all`, nawigacja po drzewie,
* Selektory CSS: `select`, `select_one` — zwięzły język zapytań do drzewa HTML,
* Porównanie obu podejść na tych samych danych,
* Ekstrakcja danych z lokalnego serwera Flask (listing, strony detali, paginacja).

Narzędzia: Python (BeautifulSoup, `requests`, Flask), VSCode.

---

# Przygotowanie

Środowisko pracy jest takie samo jak na poprzednich labach: VSCode, dwa terminale (serwer + klient), Flask.

Zainstaluj BeautifulSoup:

```bash
pip install beautifulsoup4
```

Sprawdź:

```bash
python -c "from bs4 import BeautifulSoup; print('OK')"
```

Utwórz nowy folder roboczy (np. `lab5/`) i otwórz go w VSCode.

::: {.callout-tip}
## Instalacja pakietów w pracowni
Komputery w pracowni mogą resetować pakiety między sesjami. Na początku każdego labu sprawdź, czy `beautifulsoup4` i `flask` są dostępne, i w razie potrzeby zainstaluj je ponownie.
:::

---

# Demonstracja: od regex do BeautifulSoup

Na Labie 4 napisałeś crawlera, który przechodzi po stronach katalogu miast i zbiera dane. Parsowanie HTML opierało się na wyrażeniach regularnych:

```python
ROW_PATTERN = r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>"
NEXT_LINK_PATTERN = r'<a href="([^"]+)">Następna'

rows = re.findall(ROW_PATTERN, html)
match = re.search(NEXT_LINK_PATTERN, html)
```

Teraz zastąpimy te wyrażenia regularne parserem HTML. Serwer i logika crawlera (pętla `while`, `requests.get`, zapis do JSON) zostają bez zmian — zmieniamy **tylko sposób wyciągania danych z HTML**.

## Krok 1: uruchom serwer miast z Labu 4

Skopiuj plik `app.py` z serwera miast (Lab 4) do folderu `lab5/` i uruchom w **Terminalu 1**:

```bash
flask run --debug -p 5000
```

Sprawdź w przeglądarce: `http://127.0.0.1:5000/catalog?page=1`.

## Krok 2: crawler z BeautifulSoup

Utwórz plik `crawler_bs4.py` w **Terminalu 2**. Poniżej pełny kod — porównaj go z wersją z Labu 4:

```python
import json
import requests
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:5000"


def crawl_catalog(start_url):
    all_cities = []
    url = start_url

    while url is not None:
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # --- Ekstrakcja danych ---
        table = soup.find("table")
        for row in table.find_all("tr")[1:]:       # [1:] pomija nagłówek
            cells = row.find_all("td")
            all_cities.append({
                "name": cells[0].get_text(strip=True),
                "population": int(cells[1].get_text(strip=True)),
                "voivodeship": cells[2].get_text(strip=True),
            })

        # --- Nawigacja ---
        next_a = soup.find("a", string="Następna →")
        url = BASE + next_a["href"] if next_a else None

        print(f"Pobrano stronę, łącznie miast: {len(all_cities)}")

    return all_cities


cities = crawl_catalog(f"{BASE}/catalog?page=1")
print(f"\nZebrano {len(cities)} miast.")

with open("cities.json", "w", encoding="utf-8") as f:
    json.dump(cities, f, ensure_ascii=False, indent=2)

print("Zapisano do cities.json")
```

Uruchom:

```bash
python crawler_bs4.py
```

::: {.callout-note}
## Checkpoint
1. Czy crawler zebrał 30 miast (tak jak wersja z regex)?
2. Czy plik `cities.json` jest identyczny z wersją z Labu 4?
3. Porównaj fragment parsowania (10 linii) z wersją regex. Która jest czytelniejsza?
:::

## Co się zmieniło — i co zostało

| Element | Lab 4 (regex) | Lab 5 (BeautifulSoup) |
|---------|---------------|----------------------|
| Pobranie strony | `requests.get(url)` | `requests.get(url)` — bez zmian |
| Parsowanie | `re.findall(PATTERN, html)` | `soup.find("table")` → `find_all("tr")` → `find_all("td")` |
| Nawigacja | `re.search(r'href="([^"]+)">Następna', html)` | `soup.find("a", string="Następna →")` |
| Pętla crawlera | `while url is not None` | `while url is not None` — bez zmian |
| Zapis do JSON | `json.dump(...)` | `json.dump(...)` — bez zmian |

Zmieniliśmy **4 linijki** kodu parsowania. Logika programu jest identyczna.

::: {.callout-tip}
## `find` z argumentem `string`
`soup.find("a", string="Następna →")` szuka tagu `<a>`, którego tekst to dokładnie `"Następna →"`. To odpowiednik filtrowania po atrybutach (`class_=`, `href=`), ale dla zawartości tekstowej elementu. Jeśli tekst nie pasuje dokładnie, `find` zwraca `None`.
:::

---

# Ćwiczenie 1: ekstrakcja z bookshop — `find` / `find_all`

## Uruchomienie serwera bookshop

Zatrzymaj serwer miast (`Ctrl+C` w Terminalu 1). Sklonuj i uruchom serwer księgarni:

```bash
git clone https://github.com/rodakt/bookshop.git
cd bookshop
pip install flask
flask run --debug -p 5000
```

Otwórz `http://127.0.0.1:5000/books` w przeglądarce. Zobaczysz listę książek z tytułami, autorami i cenami. Kliknij w tytuł — przejdziesz na stronę detali (`/book/1`, `/book/2`, ...).

::: {.callout-note}
## Checkpoint
Otwórz **Zbadaj** (F12) na stronie `/books`. Znajdź elementy z klasami: `.book-list`, `.book`, `.title`, `.author`, `.price`, `.book-link`. Sprawdź, jak wygląda kontener paginacji (`.pagination`, `a.next-page`, `a.prev-page`).
:::

## Zadanie: ekstrakcja z jednej strony

Utwórz plik `bookshop_find.py` i uzupełnij szkielet:

```python
import requests
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:5000"

# --- Część A: listing ---

r = requests.get(f"{BASE}/books")
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")

books = []
# 1. Znajdź wszystkie elementy książek.
#    Wskazówka: każda książka jest w elemencie z klasą "book".
# --- Twój kod ---

for book_el in ...:  # <- uzupełnij
    # 2. Wyciągnij tytuł (tag h2 z klasą "title"), autora (klasa "author")
    #    i cenę (klasa "price"). Użyj find() i get_text(strip=True).
    # --- Twój kod ---

    # 3. Wyciągnij URL strony detali z linku (tag <a> z klasą "book-link").
    #    Pamiętaj: href jest ścieżką względną — potrzebujesz BASE + href.
    # --- Twój kod ---

    books.append({
        "title": ...,
        "author": ...,
        "price": ...,
        "detail_url": ...,
    })

print(f"Znaleziono {len(books)} książek na stronie:")
for b in books:
    print(f"  {b['title']} — {b['author']} — {b['price']}")


# --- Część B: strona detali ---

# 4. Weź URL pierwszej książki z listy i pobierz stronę detali.
# --- Twój kod ---

detail_soup = BeautifulSoup(...)  # <- uzupełnij

# 5. Wyciągnij: tytuł (h1.title), autora, opis (klasa "description"),
#    cenę i stan magazynowy (klasa "stock").
#    Użyj find() na detail_soup.
# --- Twój kod ---

print(f"\nSzczegóły: {title}")
print(f"  Autor: {author}")
print(f"  Cena: {price}")
print(f"  Opis: {description[:80]}...")
print(f"  Magazyn: {stock}")
```

::: {.callout-note}
## Checkpoint
1. Czy Część A wypisuje 5 książek (tyle jest na jednej stronie)?
2. Czy Część B poprawnie wyciąga opis i stan magazynowy z detali?
3. Czy `detail_url` to pełny URL (np. `http://127.0.0.1:5000/book/1`), nie sama ścieżka?
:::

---

# Ćwiczenie 2: ekstrakcja z bookshop — selektory CSS

To samo zadanie co w Ćwiczeniu 1 — ale zamiast `find` / `find_all` używasz `select` / `select_one`.

Utwórz plik `bookshop_css.py` i uzupełnij szkielet:

```python
import requests
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:5000"

r = requests.get(f"{BASE}/books")
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")

books = []

# 1. Znajdź wszystkie elementy książek selektorem CSS.
#    Wskazówka: selektor klasy to ".nazwaklasy".
for book_el in soup.select("..."):  # <- uzupełnij selektor
    # 2. Wyciągnij tytuł, autora, cenę i link do detali.
    #    Użyj select_one() z selektorem CSS.
    #    Przykład: book_el.select_one("h2.title")
    title = book_el.select_one("...").get_text(strip=True)    # <- uzupełnij
    author = book_el.select_one("...").get_text(strip=True)   # <- uzupełnij
    price = book_el.select_one("...").get_text(strip=True)    # <- uzupełnij
    detail_url = BASE + book_el.select_one("...")["href"]     # <- uzupełnij

    books.append({
        "title": title,
        "author": author,
        "price": price,
        "detail_url": detail_url,
    })

# 3. Pobierz stronę detali pierwszej książki i wyciągnij dane
#    selektorami CSS.
# --- Twój kod ---

# 4. Wypisz wyniki — porównaj z Ćwiczeniem 1.
for b in books:
    print(f"  {b['title']} — {b['author']} — {b['price']}")
```

::: {.callout-note}
## Checkpoint
1. Czy wyciągnięte dane (tytuły, autorzy, ceny) zgadzają się z Ćwiczeniem 1?
2. Porównaj kod obu wersji. Ile linii zajmuje ekstrakcja w `find`/`find_all` vs `select`/`select_one`?
3. Która wersja jest czytelniejsza? Dlaczego?
:::

## Porównanie: `find` vs `select` na bookshop

Po ukończeniu obu ćwiczeń porównaj kluczowe fragmenty:

| Operacja | `find` / `find_all` | `select` / `select_one` |
|----------|---------------------|------------------------|
| Wszystkie książki | `soup.find_all("div", class_="book")` | `soup.select(".book")` |
| Tytuł w książce | `book_el.find("h2", class_="title")` | `book_el.select_one("h2.title")` |
| Link do detali | `book_el.find("a", class_="book-link")["href"]` | `book_el.select_one("a.book-link")["href"]` |
| Następna strona | `soup.find("a", class_="next-page")` | `soup.select_one("a.next-page")` |

W tym przypadku oba podejścia są zbliżone. Przewaga `select` rośnie przy bardziej złożonych zapytaniach — np. `"div.book-list .book h2.title"` zamiast trzech zagnieżdżonych `find`.

---

# Ćwiczenie 3: pełny crawl bookshop

Połącz wiedzę z Ćwiczeń 1–2 i Demonstracji: napisz crawlera, który przejdzie po **wszystkich stronach** listingu bookshop, wejdzie na **każdą stronę detali** i zbierze pełne dane o wszystkich książkach.

## Wymagania

1. Zacznij od `http://127.0.0.1:5000/books`.
2. Na każdej stronie listingu:
    * wyciągnij dane podstawowe każdej książki (tytuł, autor, cena),
    * wyciągnij URL strony detali każdej książki,
    * znajdź link do następnej strony (`a.next-page`). Jeśli go nie ma — koniec.
3. Dla każdej książki wejdź na stronę detali i pobierz: opis, stan magazynowy.
4. Zapisz wszystkie dane do pliku `bookshop.json`.

## Szkielet

```python
import json
import requests
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:5000"


def get_book_detail(url):
    """Pobiera stronę detali i zwraca opis oraz stan magazynowy."""
    # --- Twój kod ---
    pass


def crawl_bookshop(start_url):
    """Przechodzi po stronach listingu, zbiera dane o książkach."""
    all_books = []
    url = start_url

    while url is not None:
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # 1. Wyciągnij książki z bieżącej strony.
        # --- Twój kod ---

        # 2. Dla każdej książki pobierz stronę detali (get_book_detail).
        # --- Twój kod ---

        # 3. Znajdź link do następnej strony.
        # --- Twój kod ---

        print(f"Strona pobrana, łącznie książek: {len(all_books)}")

    return all_books


books = crawl_bookshop(f"{BASE}/books")
print(f"\nZebrano {len(books)} książek.")

with open("bookshop.json", "w", encoding="utf-8") as f:
    json.dump(books, f, ensure_ascii=False, indent=2)

print("Zapisano do bookshop.json")
```

Wybierz metodę: `find`/`find_all`, selektory CSS, albo mieszankę obu. Nie ma jednego „poprawnego" podejścia.

::: {.callout-tip}
## Wskazówka: nawigacja
Link do następnej strony ma klasę `next-page`. Jeśli używasz CSS: `soup.select_one("a.next-page")`. Jeśli używasz `find`: `soup.find("a", class_="next-page")`. W obu przypadkach sprawdź, czy wynik to `None` (ostatnia strona).
:::

::: {.callout-note}
## Checkpoint
1. Ile książek zebrał crawler? Otwórz `bookshop.json` — czy każda ma tytuł, autora, cenę, opis i stan magazynowy?
2. Czy crawler zatrzymał się na ostatniej stronie (nie zapętlił się)?
3. Porównaj strukturę crawlera z Demonstracją (serwer miast). Pętla `while`, `requests.get`, `BeautifulSoup`, sprawdzenie `next` — wzorzec jest identyczny. Zmieniły się selektory i struktura danych.
:::

---

# Ćwiczenie 4 (dodatkowe): Hacker News

Hacker News (`https://news.ycombinator.com`) to serwis agregujący linki — ma bardzo stabilną strukturę HTML, która niemal nie zmienia się od lat.

Otwórz stronę w przeglądarce i użyj **Zbadaj** (F12), żeby przyjrzeć się strukturze. Zwróć uwagę na klasy: `.titleline` (tytuł z linkiem), `.score` (punkty), `.subtext` (metadane: autor, czas, komentarze).

## Zadanie

Napisz skrypt `hackernews.py`, który pobiera **jedną stronę** (stronę główną) i wyciąga z niej listę wpisów. Dla każdego wpisu zbierz:

* tytuł,
* URL (atrybut `href` z linku w `.titleline`),
* liczbę punktów (tekst z `.score`, np. `"153 points"` → `153`),
* liczbę komentarzy (ostatni link w `.subtext`, np. `"87 comments"` → `87`).

Zapisz wyniki do `hackernews.json`.

::: {.callout-warning}
## Tylko jedna strona
Pobierasz jedną stronę — jeden `requests.get`. Nie przechodzimy po kolejnych stronach, nie klikamy w linki. To ćwiczenie na **ekstrakcję**, nie na crawling.
:::

::: {.callout-tip}
## Wskazówki

* Struktura HN to tabela. Każdy wpis to para wierszy `<tr>`: pierwszy (z klasą `athing`) zawiera tytuł i link, drugi — metadane (punkty, komentarze).
* Nie wszystkie wpisy mają punkty (np. wpisy „Ask HN" mogą nie mieć). Zabezpiecz się przed `None`.
* Liczbę komentarzy wyciągniesz z tekstu linku — szukaj tekstu kończącego się na `"comments"` lub `"comment"`. Wpisy bez komentarzy mogą mieć tekst `"discuss"`.
* Zacznij od wyciągnięcia samych tytułów — to najprostsze. Potem dodawaj kolejne pola.
:::

::: {.callout-note}
## Checkpoint
1. Czy wyciągnąłeś ~30 wpisów (tyle jest na stronie głównej)?
2. Czy punkty i komentarze to liczby (`int`), nie stringi?
3. Otwórz `hackernews.json` — czy dane wyglądają sensownie?
:::

---

# Podsumowanie

W tym labie:

* zastąpiłeś wyrażenia regularne parserem HTML (BeautifulSoup) — ten sam crawler, czytelniejszy kod,
* poznałeś dwa sposoby wyszukiwania elementów: `find`/`find_all` (pythonowe API) i `select`/`select_one` (selektory CSS),
* wyciągałeś dane z lokalnego serwera bookshop — zarówno z listingu, jak i ze stron detali,
* napisałeś crawlera, który łączy nawigację po stronach z ekstrakcją danych — wzorzec znany z Labu 4, ale z lepszymi narzędziami.

**Co dalej:**

* **Lab 6**: XPath na tych samych stronach — trzecia metoda selekcji, najsilniejsza przy złożonych strukturach i nawigacji po relacjach (osie, predykaty).