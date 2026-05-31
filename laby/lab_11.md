---
title: "Lab 11: Pierwszy spider Scrapy"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Na Labie 10 zakończyliśmy „programatyczny tor": ręcznie składaliśmy kontrolę współbieżności, timeouty, obsługę błędów i zapis wyników. Dziś oddajemy tę infrastrukturę frameworkowi. Przepiszemy crawlery, które już znasz (miasta z Lab 4, bookshop z Lab 5–6), na spidery Scrapy — ten sam serwer, ten sam wynik, znacznie mniej kodu.

Zakres materiału:

* struktura projektu Scrapy — `scrapy startproject`, `scrapy genspider`, role plików,
* `scrapy shell` — interaktywna eksploracja selektorów przed napisaniem spidera,
* spider: `start_urls`, metoda `parse`, `yield dict`,
* paginacja przez `response.follow(next_page, callback=self.parse)`,
* wzorzec lista → detal: dwa callbacki (`parse` podąża za linkami, `parse_book` wyciąga dane),
* selektory Scrapy: `response.css()` i `response.xpath()`, `.get()` / `.getall()`, `::text`, `::attr()`,
* eksport: `scrapy crawl ... -o plik.json` (oraz `.csv`, `.jsonl`),
* porównanie ręcznego crawlera z wersją w Scrapy.

Narzędzia: Python (Scrapy, Flask), VSCode.

---

# Przygotowanie

Środowisko jak na poprzednich labach: VSCode, dwa terminale (serwer w **Terminalu 1**, klient/Scrapy w **Terminalu 2**).

Utwórz folder roboczy `lab11/` i otwórz go w VSCode.

Zainstaluj Scrapy:

```bash
pip install scrapy
```

Sprawdź:

```bash
scrapy version
```

::: {.callout-tip}
## Pakiety w pracowni
Scrapy to pierwszy nowy pakiet od kilku labów. Jeśli pracownia resetuje pakiety między sesjami (GoBack), zainstaluj go ponownie na początku zajęć. `flask` znasz z wcześniejszych labów.
:::

Będą nam potrzebne dwa znane serwery:

* **serwer miast** — `app.py` z Lab 4 (katalog miast z paginacją),
* **serwer bookshop** — repozytorium z Lab 5–6.

Skopiuj `app.py` serwera miast z Lab 4 do `lab11/`. Bookshop sklonujemy później, gdy będzie potrzebny.

---

# Wstęp: gdzie jesteśmy

Twój ręczny crawler z Lab 4 wyglądał tak (szkielet):

```python
all_cities = []
url = start_url

while url is not None:
    r = requests.get(url)
    r.raise_for_status()
    # ... wyciągnij wiersze ...
    # ... znajdź link "Następna", zbuduj pełny URL albo None ...

with open("cities.json", "w", encoding="utf-8") as f:
    json.dump(all_cities, f, ensure_ascii=False, indent=2)
```

W tym schemacie ręcznie obsługujesz: pętlę po stronach, `requests.get`, budowanie pełnych URL-i z relatywnych ścieżek, warunek końca, zapis do pliku. Na Labie 10 dorzuciliśmy do tego współbieżność, `Semaphore`, timeouty i obsługę błędów — kolejne dziesiątki linii infrastruktury.

Scrapy przejmuje to wszystko. Ty piszesz **tylko logikę specyficzną dla strony**: które elementy wyciągnąć i za którymi linkami podążać. Resztą — kolejką URL-i, pobieraniem, współbieżnością, deduplikacją, eksportem — zajmuje się framework.

Plan labu: najpierw projekt i `scrapy shell` (Demo 1–2), potem prowadzone przepisanie crawlera miast (Demo 3 — to samo zadanie co Lab 4), wreszcie samodzielny spider bookshop w układzie lista → detal (Ćwiczenie 1).

---

# Demonstracja 1: projekt Scrapy

Scrapy organizuje kod w projekt o ustalonej strukturze. W **Terminalu 2** (w folderze `lab11/`) utwórz projekt:

```bash
scrapy startproject apd
cd apd
```

Powstaje struktura:

```
apd/
├── scrapy.cfg              # konfiguracja deploymentu — nie ruszamy
└── apd/
    ├── __init__.py
    ├── items.py            # struktury danych — Lab 12
    ├── middlewares.py      # nie ruszamy
    ├── pipelines.py        # przetwarzanie wyników — Lab 12
    ├── settings.py         # konfiguracja
    └── spiders/            # tu trafiają spidery
        └── __init__.py
```

Na tym labie dotykamy tylko katalogu `spiders/`. Plikami `items.py` i `pipelines.py` zajmiemy się na Labie 12.

Wygeneruj szkielet spidera:

```bash
scrapy genspider cities 127.0.0.1
```

Powstaje `apd/spiders/cities.py` z zalążkiem klasy. Wszystkie polecenia `scrapy crawl` uruchamiamy **z wnętrza folderu `apd/`** (tam, gdzie leży `scrapy.cfg`).

::: {.callout-warning}
## `genspider` generuje `https` bez ścieżki
Wygenerowany plik ma `start_urls = ["https://127.0.0.1"]` — z `https` i bez ścieżki. Za chwilę poprawimy to ręcznie na właściwy adres `http` z trasą `/catalog`.
:::

---

# Demonstracja 2: `scrapy shell`

Zanim napiszesz selektory w spiderze, warto je sprawdzić na żywo. `scrapy shell` pobiera stronę i daje gotowy obiekt `response` do eksperymentów — bez uruchamiania całego spidera.

Uruchom serwer miast w **Terminalu 1** (z folderu `lab11/`, gdzie skopiowałeś `app.py`):

```bash
flask run --debug -p 5000
```

W **Terminalu 2** (z wnętrza `apd/`) otwórz shell na pierwszej stronie katalogu:

```bash
scrapy shell "http://127.0.0.1:5000/catalog?page=1"
```

Dostajesz `response`. Wypróbuj selektory:

```python
# Wszystkie wiersze tabeli poza nagłówkiem
response.xpath('//table//tr[position()>1]')

# Nazwa miasta z pierwszego wiersza danych
response.xpath('//table//tr[position()>1][1]/td[1]/text()').get()

# Href linku "Następna"
response.xpath('//a[contains(text(),"Następna")]/@href').get()
```

::: {.callout-tip}
## `.get()` i `.getall()`
Selektor Scrapy zwraca `SelectorList`. `.get()` wyciąga pierwszy wynik jako string (lub `None`), `.getall()` — listę wszystkich. To odpowiedniki `select_one` / `select` z BeautifulSoup, ale wbudowane w `response` — bez importu bs4 czy lxml.
:::

Zamknij shell przez `exit()`. Selektory, które zadziałały w shellu, przeniesiemy teraz do spidera.

---

# Demonstracja 3: crawler miast jako spider

To dokładnie zadanie z Lab 4 — przejść po wszystkich stronach katalogu i zebrać miasta — ale w Scrapy. Otwórz `apd/spiders/cities.py` i zastąp wygenerowany szkielet:

```python
import scrapy


class CitiesSpider(scrapy.Spider):
    name = "cities"
    allowed_domains = ["127.0.0.1"]
    start_urls = ["http://127.0.0.1:5000/catalog?page=1"]

    def parse(self, response):
        for row in response.xpath('//table//tr[position()>1]'):
            yield {
                "name": row.xpath('td[1]/text()').get(),
                "population": int(row.xpath('td[2]/text()').get()),
                "voivodeship": row.xpath('td[3]/text()').get(),
            }

        next_page = response.xpath('//a[contains(text(),"Następna")]/@href').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

Dwie linijki kończą crawl, których w Lab 4 nie było:

* **`yield dict`** — spider nie buduje listy `all_cities`. Każdy słownik **generuje** (`yield`), a Scrapy zbiera wyniki i eksportuje sam.
* **`yield response.follow(next_page, callback=self.parse)`** — zamiast ręcznie budować pełny URL i wrzucać go do pętli, podajesz relatywną ścieżkę i callback. `response.follow` rozwiązuje URL względem bieżącej strony i przekazuje żądanie do kolejki. Brak pętli `while`, brak zbioru `visited` (Scrapy deduplikuje URL-e sam).

Uruchom crawl z eksportem (z wnętrza `apd/`):

```bash
scrapy crawl cities -O cities.json
```

::: {.callout-warning}
## `-o` dopisuje, `-O` nadpisuje
Mała litera `-o` **dopisuje** do istniejącego pliku — uruchomienie dwa razy da duplikaty. Wielka litera `-O` **nadpisuje**. Przy iterowaniu nad spiderem używaj `-O`.
:::

Otwórz `cities.json`. Powinno być 30 miast — tyle, ile zebrał ręczny crawler z Lab 4.

::: {.callout-note}
## Kolejność elementów ≠ kolejność stron
Scrapy pobiera strony **współbieżnie** (jak async z Lab 9–10), więc miasta w `cities.json` mogą być w innej kolejności niż w pliku z Lab 4. To nie błąd. Porównuj dane jako zbiór (posortowane), nie linia po linii:

```python
import json
a = json.load(open("cities.json", encoding="utf-8"))
b = json.load(open("../cities_lab4.json", encoding="utf-8"))  # plik z Lab 4
key = lambda c: c["name"]
assert sorted(a, key=key) == sorted(b, key=key)
```
:::

## Porównanie

Zestaw `parse` (kilkanaście linii) z funkcją `crawl_catalog` z Lab 4. Policz, co zniknęło: pętla `while`, `requests.get` z `raise_for_status`, ręczne budowanie pełnego URL-a, warunek końca, `json.dump`, importy `requests`/`re`/`json`. Zostało: selektory i `response.follow`. To jest miara tego, co Scrapy bierze na siebie.

---

# Ćwiczenie 1: spider bookshop — lista → detal

Crawler miast czytał wszystkie dane z jednej tabeli. Bookshop ma strukturę dwupoziomową: listing `/books` (tytuł, autor, cena, link) i strony detali `/book/<id>` (dodatkowo opis i stan magazynowy). Na Labie 5–6 obsłużyłeś to ręcznie — pętlą po stronach plus osobne `requests.get` na każdą stronę detali. W Scrapy ten wzorzec to **dwa callbacki**.

## Uruchomienie serwera bookshop

Zatrzymaj serwer miast (`Ctrl+C` w Terminalu 1). Sklonuj i uruchom bookshop:

```bash
git clone https://github.com/rodakt/bookshop.git
cd bookshop
flask run --debug -p 5000
```

Otwórz `http://127.0.0.1:5000/books` w przeglądarce, kliknij w tytuł — przejdziesz na stronę detali. Klasy CSS znasz z Lab 5: `.book`, `h2.title`, `.author`, `.price`, `a.book-link`, `a.next-page`; na detalach `h1.title`, `.description`, `.stock`.

::: {.callout-tip}
## Sprawdź selektory w shellu
Zanim napiszesz spidera, otwórz `scrapy shell "http://127.0.0.1:5000/books"` i przetestuj: `response.css("a.book-link::attr(href)").getall()`, `response.css("a.next-page::attr(href)").get()`. Potem shell na stronie detali, np. `response.css("h1.title::text").get()`.
:::

## Zadanie

Wygeneruj spidera:

```bash
scrapy genspider books 127.0.0.1
```

Otwórz `apd/spiders/books.py` i uzupełnij szkielet:

```python
import scrapy


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["127.0.0.1"]
    start_urls = ["http://127.0.0.1:5000/books"]

    def parse(self, response):
        # 1. Dla każdego linku do książki (a.book-link) podążaj na stronę
        #    detali z callbackiem self.parse_book.
        #    Wskazówka: response.follow przyjmuje selektor <a> wprost —
        #    sam wyciągnie z niego href.
        # --- Twój kod ---

        # 2. Znajdź link do następnej strony (a.next-page). Jeśli istnieje —
        #    podążaj za nim z callbackiem self.parse (ta sama metoda,
        #    kolejna strona listingu).
        # --- Twój kod ---

    def parse_book(self, response):
        # 3. Ze strony detali wyciągnij i wygeneruj słownik:
        #    title (h1.title), author, description, price, stock.
        #    Użyj response.css(...) z ::text i .get().
        # --- Twój kod ---
        pass
```

Uruchom i wyeksportuj (z wnętrza `apd/`):

```bash
scrapy crawl books -O bookshop.json
```

::: {.callout-tip}
## Selektor jako argument `response.follow`
`response.follow(link, callback=...)` przyjmuje nie tylko string z URL-em, ale też obiekt `<a>` — Scrapy sam wyciągnie `href`. Dzięki temu krok 1 może wyglądać tak:

```python
for link in response.css("a.book-link"):
    yield response.follow(link, callback=self.parse_book)
```
:::

::: {.callout-note}
## Checkpoint
1. Ile książek zebrał spider? Czy zgadza się z liczbą z `bookshop.json` z Lab 5?
2. Czy każdy rekord ma pola `title`, `author`, `description`, `price`, `stock`?
3. **Test regresji**: porównaj dane (posortowane po `title`) z `bookshop.json` z Lab 5. Powinny być identyczne — ta sama strona, inne narzędzie, ten sam wynik. Jeśli się różnią, gdzieś jest błąd w selektorze.
4. Czy spider zatrzymał się sam (nie zapętlił)? Scrapy deduplikuje URL-e, więc nawet gdy ostatnia strona linkuje wstecz, nie pobierze jej ponownie.
:::

---

# Ćwiczenia samodzielne

## Ćwiczenie A: formaty eksportu

Uruchom spidera `books` z różnymi rozszerzeniami pliku wyjściowego:

```bash
scrapy crawl books -O bookshop.csv
scrapy crawl books -O bookshop.jsonl
```

Otwórz oba pliki. Scrapy rozpoznaje format po rozszerzeniu: `.csv` to tabela (pierwszy wiersz to nazwy pól), `.jsonl` (JSON Lines) to jeden obiekt JSON na linię. Które ułatwia podgląd pojedynczego rekordu w edytorze, a które — wczytanie do arkusza?

## Ćwiczenie B: spider na serwer szczytów

Na Labie 4 (Ćwiczenie 2) zbudowałeś serwer `/peaks` — katalog polskich szczytów z paginacją (klucze `name`, `height`, `range`). Uruchom go i napisz spidera `peaks`.

Punkt wyjścia: skopiuj `cities.py`, zmień `name`, `start_urls` i selektory/klucze. **Logika spidera — pętla po stronach przez `response.follow`, `yield dict` — jest identyczna.** Zmieniasz tylko cel i nazwy pól. To ta sama zasada „jedna zmienna na raz", którą widziałeś przy przejściu z miast na szczyty w Lab 4.

Wynik: `peaks.json` z 20 szczytami.

## Ćwiczenie C (dodatkowe): zagadki w `scrapy shell`

Otwórz shell na listingu bookshop:

```bash
scrapy shell "http://127.0.0.1:5000/books"
```

Rozwiąż w jednej linii każde (echo „dziesięciu zapytań XPath" z Lab 6, tym razem mieszanką CSS i XPath):

1. Tytuły wszystkich książek na stronie (lista stringów).
2. Liczba książek na stronie.
3. Wszystkie wartości `href` linków do detali (`a.book-link`).
4. Href linku do następnej strony.
5. Cena książki „Pan Tadeusz" — dojdź do niej osią XPath od jej tytułu.

::: {.callout-tip}
## CSS vs XPath w jednym `response`
`response.css(...)` i `response.xpath(...)` działają na tym samym obiekcie — możesz nawet je łączyć (`response.css("div.book").xpath('./h2/text()')`). Zadania 1–4 są wygodniejsze w CSS, zadanie 5 (nawigacja osią) — w XPath.
:::

---

# Podsumowanie

W tym labie:

* utworzyłeś projekt Scrapy (`startproject`, `genspider`) i poznałeś role plików — na tym labie dotykaliśmy tylko `spiders/`,
* używałeś `scrapy shell` do sprawdzania selektorów na żywo, zanim trafiły do spidera,
* przepisałeś crawler miast z Lab 4 na spidera — to samo zadanie, ten sam wynik, kilkanaście linii zamiast pętli z ręcznym pobieraniem, budowaniem URL-i i zapisem,
* zobaczyłeś, że Scrapy pobiera strony współbieżnie, więc kolejność wyników nie odpowiada kolejności stron — dane porównujemy jako zbiór,
* napisałeś spidera bookshop w układzie **lista → detal**: `parse` podąża za linkami (do detali i do następnej strony), `parse_book` wyciąga pełne dane,
* eksportowałeś wyniki do JSON, CSV i JSON Lines jednym przełącznikiem `-O`.

Mapa „ręcznie → Scrapy", którą warto zapamiętać:

| Ręcznie (Lab 4–10) | Scrapy |
|---|---|
| `to_visit`, `visited`, pętla `while` | kolejka i deduplikacja Schedulera |
| `requests.get(url)` | Downloader (pobiera, podajesz tylko URL) |
| budowanie pełnego URL z relatywnej ścieżki | `response.follow` |
| `BeautifulSoup` / `lxml` + selektory | `response.css()` / `response.xpath()` |
| `json.dump` / `csv.writer` | `scrapy crawl ... -O plik.json` |
| `Semaphore`, `gather` (Lab 10) | współbieżność wbudowana w Engine |

**Co dalej:**

* **Wykład 6 (przypomnienie)**: poznane na wykładzie `Item` i `Item Pipeline` to deklaratywna struktura danych i łańcuch czyszczenia/walidacji — dotąd ich nie używaliśmy.
* **Lab 12**: `Item` i `ItemPipeline` w praktyce — czyszczenie cen (`"34,90 zł"` → `34.90`), walidacja, zapis przez pipeline. Konfiguracja tempa w `settings.py`. Studium przypadku na realnej stronie: `books.toscrape.com` (serwis stworzony do nauki scrapingu).