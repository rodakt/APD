---
title: "Wykład 6: Scrapy — framework do web scrapingu"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

## Cele i zakres

Dotychczas budowaliśmy każdy element łańcucha pozyskiwania danych osobno: klient HTTP (`requests`), parsowanie HTML (BeautifulSoup, lxml), logika crawlingu (zbiór odwiedzonych URL-ów, pętla), zapis wyników (JSON, CSV). Każdy z tych elementów działał, ale sklejanie ich wymagało powtarzalnego kodu — obsługi błędów, opóźnień między żądaniami, śledzenia odwiedzonych stron, eksportu do pliku. Przy większych projektach ten kod rośnie szybciej niż logika ekstrakcji.

Scrapy to framework, który przejmuje tę infrastrukturę. Scrapy zajmuje się pobieraniem, kolejkowaniem URL-ów, kontrolą tempa, eksportem i obsługą błędów.

Zakres obejmuje:

* ręczny scraper vs framework — co zyskujemy,
* architektura Scrapy — Engine, Scheduler, Downloader, Spider, Item Pipeline,
* struktura projektu — `scrapy startproject`, pliki i ich role,
* spider — `start_urls`, metoda `parse`, `yield dict`, `yield Request`,
* selektory w Scrapy — `response.css()`, `response.xpath()`, `.get()`, `.getall()`,
* Item i Item Pipeline — deklaratywna struktura danych, czyszczenie, walidacja, zapis,
* konfiguracja — `settings.py`, kontrola tempa i współbieżności,
* `robots.txt` i etyka scrapingu.

## Serwer ćwiczeniowy

Przykłady w tym wykładzie zakładają lokalny serwer Flask udający prostą księgarnię. Kod serwera dostępny jest w repozytorium kursu:

<https://github.com/rodakt/APD/tree/v_2526/bookshop>

Aby pobrać tylko katalog `bookshop` bez klonowania całego repozytorium:

```bash
git clone --filter=blob:none --sparse https://github.com/rodakt/APD
cd APD
git sparse-checkout set bookshop
git checkout v_2526
```

Uruchomienie serwera:

```bash
cd bookshop
flask --app app run --debug
```

Serwer działa na `http://localhost:5000`. Strony do scrapowania: `/books` (listing z paginacją) i `/book/<id>` (strona szczegółowa).

---

## Od ręcznego scrapera do frameworka

### Ręczny crawler — przypomnienie

Na wcześniejszych labach pisaliśmy crawlery w `requests` + BeautifulSoup. Schemat wyglądał mniej więcej tak:

```python
import requests
from bs4 import BeautifulSoup

visited = set()
to_visit = ["http://localhost:5000/books"]
results = []

while to_visit:
    url = to_visit.pop(0)
    if url in visited:
        continue
    visited.add(url)

    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    for book in soup.select("div.book"):
        results.append({
            "title": book.select_one("h2").text.strip(),
            "price": book.select_one("span.price").text.strip(),
        })

    for a in soup.select("a.next-page"):
        next_url = "http://localhost:5000" + a["href"]
        if next_url not in visited:
            to_visit.append(next_url)
```

To działa, ale przy skalowaniu pojawiają się problemy:

* **Śledzenie URL-ów** — ręczny zbiór `visited`, ręczne budowanie pełnych URL-ów.
* **Obsługa błędów** — brak retry, brak reakcji na timeout, brak logowania błędów.
* **Tempo żądań** — brak opóźnień między żądaniami (ryzyko przeciążenia serwera).
* **Eksport** — ręczny `json.dump` lub `csv.writer`, osobno dla każdego formatu.
* **`robots.txt`** — trzeba samemu pobrać i sparsować plik, zanim zaczniemy crawlować.

Każdy z tych elementów można dopisać, ale to kod infrastrukturalny, który powtarza się w każdym projekcie. Framework rozwiązuje te problemy raz, a programista skupia się na tym, co jest unikalne: **logice ekstrakcji danych z konkretnej strony**.

### Co daje Scrapy

Scrapy to framework open-source, który implementuje pełny cykl crawlingu:

* kolejkowanie i deduplikacja URL-ów,
* asynchroniczne pobieranie stron (pod spodem używa Twisted — asynchronicznej biblioteki I/O),
* wbudowane selektory CSS i XPath,
* pipeline przetwarzania danych (czyszczenie, walidacja, zapis),
* konfiguracja tempa żądań, limitów współbieżności, nagłówków,
* automatyczne przestrzeganie `robots.txt`,
* eksport do JSON, CSV, XML z linii poleceń.

---

## Architektura

Scrapy składa się z kilku komponentów, z których każdy odpowiada za jeden etap cyklu:

```
                    ┌───────────┐
         URL-e      │ Scheduler │     kolejka URL-ów
        ───────────▶│           │──────────────┐
        │           └───────────┘              │
        │                                      ▼
   ┌────────┐                          ┌──────────────┐
   │ Spider │◀─── response ────────────│  Downloader   │
   │        │                          │               │
   │  parse │─── yield Request ──▶     │  HTTP GET/POST│
   │        │─── yield Item ──┐        └──────────────┘
   └────────┘                 │
                              ▼
                     ┌────────────────┐
                     │ Item Pipeline  │
                     │                │
                     │ czyszczenie    │
                     │ walidacja      │
                     │ zapis          │
                     └────────────────┘
```

**Engine** (nie pokazany na diagramie) koordynuje przepływ danych między komponentami. 

**Scheduler** przechowuje kolejkę URL-ów do odwiedzenia. Automatycznie deduplikuje — ten sam URL nie zostanie pobrany dwa razy. To odpowiednik ręcznego zbioru `visited` i listy `to_visit`.

**Downloader** pobiera strony z sieci i zwraca obiekt `response`. To odpowiednik `requests.get()`, ale asynchroniczny i z wbudowanym retry, timeoutami, opóźnieniami.

**Spider** to klasa. Otrzymuje `response` (pobraną stronę) i decyduje, co z nią zrobić: wyciągnąć dane (`yield dict` lub `yield Item`) albo podążyć za linkiem (`yield Request`). To odpowiednik logiki ekstrakcji i budowania listy kolejnych URL-ów.

**Item Pipeline** przetwarza wyekstrahowane dane: czyści, waliduje, transformuje, zapisuje. To odpowiednik ręcznego `strip()`, konwersji typów i `json.dump`.


| Ręcznie | Scrapy |
|---|---|
| `to_visit`, `visited` | Scheduler |
| `requests.get(url)` | Downloader |
| BeautifulSoup + logika ekstrakcji | Spider (`parse`) |
| `json.dump(...)` / `csv.writer(...)` | Item Pipeline + eksport |
| `time.sleep(delay)` | `DOWNLOAD_DELAY` w settings |
| ręczne parsowanie `robots.txt` | `ROBOTSTXT_OBEY` |

---

## Struktura projektu

### Tworzenie projektu

Scrapy organizuje kod w projekt z ustaloną strukturą katalogów. Projekt tworzymy poleceniem:

```bash
scrapy startproject bookshop
```

Powstaje następująca struktura:

```
bookshop/
├── scrapy.cfg              # konfiguracja deploymentu (nie ruszamy)
└── bookshop/
    ├── __init__.py
    ├── items.py            # definicje struktur danych
    ├── middlewares.py       # (nie ruszamy)
    ├── pipelines.py        # przetwarzanie wyników
    ├── settings.py         # konfiguracja projektu
    └── spiders/
        ├── __init__.py
        └── (tu będą nasze spidery)
```

Wewnątrz projektu tworzymy spidera:

```bash
cd bookshop
scrapy genspider books localhost:5000
```

To generuje plik `bookshop/spiders/books.py` z szablonem spidera.

### Pliki, z których korzystamy

Na tym wykładzie korzystamy z czterech plików:

* **`spiders/*.py`** — logika ekstrakcji (klasa Spider),
* **`items.py`** — definicja struktury danych (klasa Item),
* **`pipelines.py`** — przetwarzanie danych (klasy Pipeline),
* **`settings.py`** — konfiguracja (tempo, limity, aktywne pipeline).

`middlewares.py` i `scrapy.cfg` zostawiamy bez zmian.

---

## Spider — mechanika

Spider to klasa dziedzicząca po `scrapy.Spider`. Definiuje punkt startowy (jakie URL-e pobrać na początku) i logikę ekstrakcji (co zrobić z pobraną stroną).

### Minimalny spider

Rozważmy stronę z listą książek:

```html
<html>
<body>
  <h1>Księgarnia</h1>
  <div class="book-list">
    <div class="book">
      <h2 class="title">Solaris</h2>
      <span class="author">Stanisław Lem</span>
      <span class="price">34,90 zł</span>
    </div>
    <div class="book">
      <h2 class="title">Ferdydurke</h2>
      <span class="author">Witold Gombrowicz</span>
      <span class="price">28,50 zł</span>
    </div>
  </div>
  <a class="next-page" href="/books?page=2">Następna strona</a>
</body>
</html>
```

Spider, który wyciąga dane z tej strony:

```python
import scrapy


class BooksSpider(scrapy.Spider):
    name = "books"
    start_urls = ["http://localhost:5000/books"]

    def parse(self, response):
        for book in response.css("div.book"):
            yield {
                "title": book.css("h2.title::text").get(),
                "author": book.css("span.author::text").get(),
                "price": book.css("span.price::text").get(),
            }
```

Rozbijmy to element po elemencie:

**`name = "books"`** — unikalna nazwa spidera. Używamy jej do uruchomienia: `scrapy crawl books`.

**`start_urls`** — lista URL-ów, od których Scrapy zaczyna. Scheduler umieszcza je w kolejce, Downloader pobiera i przekazuje do metody `parse`.

**`def parse(self, response)`** — metoda wywoływana dla każdej pobranej strony. `response` to obiekt Scrapy (nie `requests.Response`) — ma wbudowane selektory CSS i XPath.

**`yield dict`** — spider nie zwraca listy wyników, tylko **generuje** (`yield`) kolejne elementy. Każdy wygenerowany słownik trafia do Item Pipeline, a stamtąd do eksportu.

### Uruchomienie i eksport

```bash
scrapy crawl books -o books.json
```

Scrapy uruchamia spidera, pobiera strony, przetwarza wyniki i zapisuje je do `books.json`. Format rozpoznawany jest po rozszerzeniu pliku:

```bash
scrapy crawl books -o books.csv
scrapy crawl books -o books.jsonl   # JSON Lines — jeden obiekt na linię
```

Bez `-o` spider działa, ale wyniki nie są zapisywane do pliku (widać je tylko w logach, jeśli ustawimy odpowiedni poziom logowania).

### Podążanie za linkami — `response.follow`

Na stronie jest link do następnej strony. Spider może za nim podążyć:

```python
def parse(self, response):
    for book in response.css("div.book"):
        yield {
            "title": book.css("h2.title::text").get(),
            "author": book.css("span.author::text").get(),
            "price": book.css("span.price::text").get(),
        }

    next_page = response.css("a.next-page::attr(href)").get()
    if next_page:
        yield response.follow(next_page, callback=self.parse)
```

`response.follow(url, callback)` tworzy nowe żądanie i przekazuje je do Schedulera. Gdy Downloader pobierze stronę, wywoła podaną metodę `callback` z nowym `response`.

`response.follow` automatycznie rozwiązuje relatywne URL-e — `"/books?page=2"` zamienia na `"http://localhost:5000/books?page=2"` na podstawie URL bieżącej strony. Nie trzeba ręcznie budować pełnego URL-a.

Scheduler automatycznie deduplikuje URL-e — jeśli strona 2 linkuje z powrotem do strony 1, Scrapy nie pobierze jej ponownie.

Jedno wywołanie `parse` może generować zarówno dane (`yield dict`), jak i nowe żądania (`yield response.follow`). Scrapy rozróżnia je automatycznie: słownik trafia do pipeline, Request trafia do Schedulera.

### `scrapy.Request` — pełna forma

`response.follow` to skrót. Pełna forma to jawne tworzenie obiektu `scrapy.Request`:

```python
yield scrapy.Request(
    url="http://localhost:5000/books?page=2",
    callback=self.parse,
)
```

Różnica: `scrapy.Request` wymaga pełnego URL-a (nie rozwiązuje relatywnych). `response.follow` jest wygodniejszy w większości przypadków. `scrapy.Request` przydaje się, gdy URL budujemy programowo, a nie wyciągamy z HTML-a.

### Wzorzec lista → detal

Częsty scenariusz: strona z listą elementów (np. lista książek) zawiera linki do stron szczegółowych, gdzie jest więcej danych.

```html
<!-- Listing: /books -->
<div class="book">
  <a class="book-link" href="/book/1">Solaris</a>
  <span class="price">34,90 zł</span>
</div>
<div class="book">
  <a class="book-link" href="/book/2">Ferdydurke</a>
  <span class="price">28,50 zł</span>
</div>
```

```html
<!-- Strona szczegółowa: /book/1 -->
<h1 class="title">Solaris</h1>
<p class="author">Stanisław Lem</p>
<p class="description">Klasyka polskiej science fiction. Naukowcy na stacji
orbitalnej badają tajemniczy ocean planety Solaris.</p>
<span class="price">34,90 zł</span>
<span class="stock">W magazynie: 7 szt.</span>
```

Spider z dwoma callbackami:

```python
class BooksSpider(scrapy.Spider):
    name = "books"
    start_urls = ["http://localhost:5000/books"]

    def parse(self, response):
        for link in response.css("a.book-link"):
            yield response.follow(link, callback=self.parse_book)

        next_page = response.css("a.next-page::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_book(self, response):
        yield {
            "title": response.css("h1.title::text").get(),
            "author": response.css("p.author::text").get(),
            "description": response.css("p.description::text").get(),
            "price": response.css("span.price::text").get(),
            "stock": response.css("span.stock::text").get(),
        }
```

Metoda `parse` przetwarza listing — nie wyciąga danych o książkach, tylko podąża za linkami do stron szczegółowych. Dla każdego linka generuje `response.follow` z callbackiem `parse_book`. Dodatkowo podąża za linkiem paginacji (z callbackiem `self.parse` — ta sama metoda, kolejna strona listingu).

Metoda `parse_book` przetwarza stronę szczegółową — wyciąga pełne dane i generuje słownik.

`response.follow(link, ...)` przyjmuje nie tylko string z URL-em, ale też obiekt selektora (tu: element `<a>`). Scrapy automatycznie wyciąga z niego atrybut `href`.

---

## Selektory w Scrapy

Na Wykładzie 3 poznaliśmy trzy metody selekcji danych z HTML: API BeautifulSoup, selektory CSS i XPath. Scrapy ma wbudowany własny mechanizm selektorów, który łączy CSS i XPath w jednym interfejsie. Nie trzeba importować BeautifulSoup ani lxml — selektory są częścią obiektu `response`.

### `response.css()` i `response.xpath()`

```python
# CSS — składnia znana z Wykładu 3
response.css("div.book h2.title::text")

# XPath — również znany z Wykładu 3
response.xpath('//div[@class="book"]/h2[@class="title"]/text()')
```

Oba zwracają obiekt `SelectorList` — listę wyników, z której wyciągamy dane:

* **`.get()`** — pierwszy wynik jako string (lub `None`, jeśli brak). Odpowiednik `select_one` w BeautifulSoup.
* **`.getall()`** — lista wszystkich wyników jako stringi. Odpowiednik `select` w BeautifulSoup.

```python
# Jeden wynik:
title = response.css("h1.title::text").get()          # "Solaris"

# Wszystkie wyniki:
prices = response.css("span.price::text").getall()     # ["34,90 zł", "28,50 zł"]
```

### Pseudoelementy `::text` i `::attr()`

Selektory CSS w Scrapy mają dwa rozszerzenia, których nie ma w standardowych selektorach CSS:

* **`::text`** — wyciąga tekst z elementu (zamiast samego elementu):

```python
response.css("h2.title::text").get()         # "Solaris"
response.css("h2.title").get()               # "<h2 class=\"title\">Solaris</h2>"
```

* **`::attr(name)`** — wyciąga wartość atrybutu:

```python
response.css("a.next-page::attr(href)").get()   # "/books?page=2"
```

W XPath te same operacje wyglądają tak:

```python
response.xpath('//h2[@class="title"]/text()').get()       # "Solaris"
response.xpath('//a[@class="next-page"]/@href').get()      # "/books?page=2"
```

### Selektory na podelementach

Selektory można łączyć w łańcuchy — najpierw wybrać kontener, potem szukać wewnątrz niego:

```python
for book in response.css("div.book"):
    # book to Selector — ma te same metody css() i xpath()
    title = book.css("h2.title::text").get()
    price = book.css("span.price::text").get()
```

To ten sam pattern co `find` + `find_all` w BeautifulSoup, ale w jednolinijkowej składni selektorowej.

### `scrapy shell` — interaktywna eksploracja

Scrapy oferuje interaktywną konsolę do testowania selektorów:

```bash
scrapy shell "http://localhost:5000/books"
```

W konsoli dostajemy obiekt `response`, na którym możemy wywoływać selektory:

```python
>>> response.css("div.book")
[<Selector query='descendant-or-self::div[...]' data='<div class="book">...'>]

>>> response.css("h2.title::text").getall()
['Solaris', 'Ferdydurke', ...]
```

Shell pozwala szybko sprawdzić, czy selektor trafia w odpowiednie elementy — zanim napiszemy spidera. Na labach będziemy z niego korzystać jako z narzędzia eksploracyjnego.

---

## Item i Item Pipeline

### Dlaczego `yield dict` nie wystarczy

W minimalnym spiderze generowaliśmy zwykłe słowniki:

```python
yield {
    "title": book.css("h2.title::text").get(),
    "price": book.css("span.price::text").get(),
}
```

To działa, ale ma ograniczenia:

* **Brak struktury** — nic nie wymusza, jakie klucze powinien mieć słownik. Literówka w nazwie klucza (`"titel"` zamiast `"title"`) nie zgłosi błędu.
* **Brudne dane** — ceny przychodzą jako `"  34,90 zł  "`, tytuły mają zbędne białe znaki, niektóre pola mogą być `None`. Czyszczenie w metodzie `parse` zaśmieca logikę ekstrakcji.
* **Brak walidacji** — spider generuje wszystko, co wyciągnie, nawet niekompletne rekordy.

Item i Pipeline rozdzielają te odpowiedzialności: spider wyciąga surowe dane, pipeline je czyści i waliduje.

### `scrapy.Item` — deklaratywna struktura

```python
# items.py
import scrapy


class BookItem(scrapy.Item):
    title = scrapy.Field()
    author = scrapy.Field()
    price = scrapy.Field()
    description = scrapy.Field()
    stock = scrapy.Field()
```

`BookItem` zachowuje się jak słownik (dostęp przez `item["title"]`, iteracja po kluczach), ale dopuszcza tylko zadeklarowane pola. Próba przypisania do niezadeklarowanego klucza zgłosi `KeyError`.

Spider zamiast `yield dict` generuje `yield BookItem(...)`:

```python
# spiders/books.py
from bookshop.items import BookItem


class BooksSpider(scrapy.Spider):
    name = "books"
    start_urls = ["http://localhost:5000/books"]

    def parse(self, response):
        for link in response.css("a.book-link"):
            yield response.follow(link, callback=self.parse_book)

        next_page = response.css("a.next-page::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_book(self, response):
        yield BookItem(
            title=response.css("h1.title::text").get(),
            author=response.css("p.author::text").get(),
            description=response.css("p.description::text").get(),
            price=response.css("span.price::text").get(),
            stock=response.css("span.stock::text").get(),
        )
```

Zmiana jest minimalna — w `parse_book` zamiast `{}` piszemy `BookItem(...)`. Metoda `parse` pozostaje taka sama jak w poprzednim przykładzie. Zysk pojawia się po stronie pipeline.

### Item Pipeline — łańcuch przetwarzania

Pipeline to klasa z metodą `process_item`, która otrzymuje każdy wygenerowany item, przetwarza go i zwraca (lub odrzuca):

```python
# pipelines.py
import scrapy


class StripWhitespacePipeline:
    def process_item(self, item, spider):
        for field in item:
            if isinstance(item[field], str):
                item[field] = item[field].strip()
        return item
```

Ten pipeline przechodzi po wszystkich polach itemu i usuwa białe znaki z początku i końca. Dostaje item z `"  Solaris  "`, zwraca item z `"Solaris"`.

Pipeline czyszczący ceny:

```python
class CleanPricePipeline:
    def process_item(self, item, spider):
        raw = item.get("price", "")
        if raw:
            cleaned = raw.replace("zł", "").replace(",", ".").strip()
            item["price"] = float(cleaned)
        return item
```

Cena `"34,90 zł"` staje się liczbą `34.9`.

Pipeline walidujący:

```python
class DropIncompletePipeline:
    def process_item(self, item, spider):
        if not item.get("title"):
            raise scrapy.exceptions.DropItem(f"Brak tytułu: {item}")
        return item
```

`DropItem` — wyjątek sygnalizujący, że item jest niekompletny i powinien zostać odrzucony. Scrapy loguje dropnięte itemy, ale nie przerywa działania spidera.

### Aktywacja pipeline w settings

Pipeline nie działa, dopóki nie aktywujemy go w `settings.py`:

```python
# settings.py
ITEM_PIPELINES = {
    "bookshop.pipelines.StripWhitespacePipeline": 100,
    "bookshop.pipelines.CleanPricePipeline": 200,
    "bookshop.pipelines.DropIncompletePipeline": 300,
}
```

Liczba oznacza priorytet — niższy numer wykonuje się wcześniej. Tu: najpierw strip białych znaków (100), potem czyszczenie ceny (200), na końcu walidacja (300).

Kolejność ma znaczenie. `CleanPricePipeline` zakłada, że `price` to string (bo wywołuje `.replace()`). Gdyby działał po sobie samym (na już skonwertowanej liczbie), rzuciłby wyjątek. Dlatego walidacja (`DropIncompletePipeline`) jest ostatnia — działa na już oczyszczonych danych.

Pipeline to łańcuch: wynik jednego `process_item` trafia jako wejście do następnego. Jeśli którykolwiek rzuci `DropItem`, reszta łańcucha jest pomijana dla tego itemu.

---

## Konfiguracja

Scrapy konfigurujemy przez `settings.py`. Poniżej kluczowe ustawienia — reszta ma sensowne wartości domyślne.

### Kontrola tempa

**`DOWNLOAD_DELAY`** — minimalne opóźnienie (w sekundach) między kolejnymi żądaniami do tego samego serwera:

```python
DOWNLOAD_DELAY = 1   # co najmniej 1 sekunda między żądaniami
```

To odpowiednik ręcznego `time.sleep(1)` w pętli crawlera, ale zintegrowany z mechanizmem pobierania. Domyślnie: `0` (brak opóźnienia).

**`CONCURRENT_REQUESTS`** — maksymalna liczba jednoczesnych żądań:

```python
CONCURRENT_REQUESTS = 8   # domyślnie 16
```

Analogia do `asyncio.Semaphore` z Wykładu 5. Scrapy nie wyśle więcej niż tyle żądań jednocześnie — reszta czeka w Schedulerze.

**`CONCURRENT_REQUESTS_PER_DOMAIN`** — limit per domena:

```python
CONCURRENT_REQUESTS_PER_DOMAIN = 4   # domyślnie 8
```

Oba limity działają jednocześnie — obowiązuje bardziej restrykcyjny.

### Identyfikacja

**`USER_AGENT`** — nagłówek identyfikujący crawlera:

```python
USER_AGENT = "bookshop-spider (+http://example.com/bot)"
```

Domyślnie Scrapy wysyła `"Scrapy/X.Y (+https://scrapy.org)"`. Ustawiamy własny, żeby administrator serwera wiedział, kto crawluje.

### `robots.txt`

**`ROBOTSTXT_OBEY`** — czy respektować plik `robots.txt`:

```python
ROBOTSTXT_OBEY = True   # domyślnie True
```

Scrapy przed pierwszym żądaniem do domeny pobiera jej `robots.txt` i sprawdza, czy nasz `USER_AGENT` ma dostęp do żądanego URL-a. Jeśli nie — pomija żądanie.

---

## `robots.txt` i etyka

### Czym jest `robots.txt`

`robots.txt` to plik tekstowy w katalogu głównym serwera, który informuje crawlery, jakie ścieżki mogą, a jakich nie powinny odwiedzać:

```
# https://example.com/robots.txt
User-agent: *
Disallow: /admin/
Disallow: /api/internal/
Allow: /

User-agent: BadBot
Disallow: /
```

Reguły:

* `User-agent: *` — dotyczy wszystkich crawlerów.
* `Disallow: /admin/` — nie crawluj ścieżek zaczynających się od `/admin/`.
* `Allow: /` — reszta dozwolona.
* Sekcja `User-agent: BadBot` blokuje konkretnego bota całkowicie.

`robots.txt` to **konwencja**, nie zabezpieczenie techniczne — nic nie powstrzymuje crawlera przed zignorowaniem tych reguł. Scrapy domyślnie je respektuje (`ROBOTSTXT_OBEY = True`).

### Dobre praktyki

* **Identyfikuj się** — ustaw `USER_AGENT` z nazwą bota i kontaktem.
* **Kontroluj tempo** — `DOWNLOAD_DELAY` chroni serwer przed przeciążeniem. Nawet jeśli `robots.txt` nie wymaga opóźnień, kilkadziesiąt żądań na sekundę do jednego serwera to zachowanie agresywne.
* **Pobieraj tylko to, czego potrzebujesz** — nie crawluj całej strony, jeśli interesuje Cię jeden dział.
* **Respektuj `robots.txt`** — to minimum etyki. Wyłączenie `ROBOTSTXT_OBEY` powinno mieć uzasadnienie (np. crawlowanie własnego serwera).

### Kontekst prawny

Sytuacja prawna web scrapingu różni się między jurysdykcjami i nie ma jednoznacznych, uniwersalnych reguł. `robots.txt` nie jest dokumentem prawnym, ale jego łamanie może być argumentem w sporze. Na tym kursie pracujemy na lokalnych serwerach i na stronach stworzonych do nauki scrapingu (np. books.toscrape.com) — nie ma tu ryzyka prawnego ani etycznego.

---

## Podsumowanie

Na tym wykładzie:

* zobaczyliśmy, że ręczny crawler wymaga dużo powtarzalnego kodu infrastrukturalnego — i że framework przejmuje tę odpowiedzialność,
* poznaliśmy architekturę Scrapy: Scheduler (kolejka URL-ów), Downloader (pobieranie), Spider (ekstrakcja), Pipeline (przetwarzanie),
* nauczyliśmy się pisać spidera: `start_urls`, `parse`, `yield dict`, `yield response.follow` z callbackiem,
* zobaczyliśmy pattern lista → detal: dwa callbacki, `parse` podąża za linkami, `parse_book` wyciąga dane,
* poznaliśmy selektory Scrapy: `response.css()`, `response.xpath()`, `.get()`, `.getall()`, pseudoelementy `::text` i `::attr()`,
* zdefiniowaliśmy `Item` jako deklaratywną strukturę danych i `Pipeline` jako łańcuch czyszczenia i walidacji,
* skonfigurowaliśmy tempo (`DOWNLOAD_DELAY`, `CONCURRENT_REQUESTS`) i `robots.txt` (`ROBOTSTXT_OBEY`).

**Co dalej:**

* **Lab 11**: Pierwszy spider — `scrapy startproject`, `scrapy shell` do eksploracji selektorów, spider na lokalnym serwerze Flask (listing książek, strony szczegółowe), eksport do JSON. Porównanie z ręcznym crawlerem.
* **Lab 12**: Pipeline i paginacja — `Item`, `ItemPipeline` (czyszczenie cen, walidacja), spider z obsługą stronicowania, studium przypadku na books.toscrape.com.