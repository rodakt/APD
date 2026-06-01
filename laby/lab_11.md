---
title: "Lab 11: Pierwszy spider Scrapy"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Na Labie 10 zakończyliśmy „programatyczny tor": ręcznie składaliśmy kontrolę współbieżności, timeouty, obsługę błędów i zapis wyników. Dziś oddajemy tę infrastrukturę frameworkowi. Przepiszemy crawlery, które już znasz, na spidery Scrapy — ten sam serwer, ten sam wynik, znacznie mniej kodu.

Zakres materiału:

* struktura projektu Scrapy — `scrapy startproject`, `scrapy genspider`, role plików,
* `scrapy shell` — interaktywna eksploracja selektorów przed napisaniem spidera,
* spider: `start_urls`, metoda `parse`, `yield dict`,
* paginacja przez `response.follow(next_page, callback=self.parse)`,
* wzorzec lista → detal: dwa callbacki,
* podążanie za pojedynczym linkiem w łańcuchu stron,
* selektory Scrapy: `response.css()` i `response.xpath()`, `.get()` / `.getall()`, `::text`, `::attr()`,
* eksport: `scrapy crawl ... -O plik.json` (oraz `.csv`, `.jsonl`),
* porównanie ręcznego crawlera z wersją w Scrapy.

Narzędzia: Python (Scrapy, Flask), VSCode.

---

# Przygotowanie

Środowisko jak na poprzednich labach: VSCode, dwa terminale (serwer w **Terminalu 1**, Scrapy w **Terminalu 2**).

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

Będą nam potrzebne trzy znane serwery — wszystkie z wcześniejszych zajęć:

* **serwer miast** — `app.py` z Lab 4 (katalog z paginacją),
* **serwer bookshop** — repozytorium z Lab 5–6,
* **serwer Collatza** — z Wykładu 2 (kod wklejony w Ćwiczeniu 2, jest krótki).

Skopiuj `app.py` serwera miast z Lab 4 do `lab11/`. Pozostałe serwery uruchomimy, gdy będą potrzebne.

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

Plan labu rośnie przez trzy kształty stron, które poznałeś ręcznie:

* **Demo** — katalog z paginacją (miasta, Lab 4), prowadzona przepiska,
* **Ćwiczenie 1** — lista → detal (bookshop, Lab 5–6), wzorzec z Wykładu 6, bez szkieletu,
* **Ćwiczenie 2** — łańcuch (Collatz, Wykład 2 / Lab 4), nowy kształt, bez szkieletu.

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
Scrapy pobiera strony **współbieżnie** (jak async z Lab 9–10), więc miasta w `cities.json` mogą być w innej kolejności niż w pliku z Lab 4. To nie błąd — przy paginacji wszystkie linki „Następna" trafiają do kolejki niemal naraz. Porównuj dane jako zbiór (posortowane), nie linia po linii.
:::

## Porównanie

Zestaw `parse` (kilkanaście linii) z funkcją `crawl_catalog` z Lab 4. Policz, co zniknęło: pętla `while`, `requests.get` z `raise_for_status`, ręczne budowanie pełnego URL-a, warunek końca, `json.dump`, importy `requests`/`re`/`json`. Zostało: selektory i `response.follow`. To jest miara tego, co Scrapy bierze na siebie.

---

# Ćwiczenie 1: spider bookshop — lista → detal

Crawler miast czytał wszystkie dane z jednej tabeli. Bookshop ma strukturę dwupoziomową: listing `/books` (tytuł, autor, cena, link) i strony detali `/book/<id>` (dodatkowo opis i stan magazynowy). W Scrapy ten wzorzec to **dwa callbacki**: `parse` podąża za linkami (do detali i do następnej strony listingu), drugi callback wyciąga dane ze strony detali.

Ten dokładnie wzorzec — z serwerem bookshop — był pokazany na **Wykładzie 6**. Tym razem piszesz spidera samodzielnie, bez szkieletu. Jeśli utkniesz, wróć do slajdów z wykładu i do `scrapy shell`.

## Uruchomienie serwera bookshop

Zatrzymaj serwer miast (`Ctrl+C` w Terminalu 1). Sklonuj i uruchom bookshop:

```bash
git clone https://github.com/rodakt/bookshop.git
cd bookshop
flask run --debug -p 5000
```

Otwórz `http://127.0.0.1:5000/books` w przeglądarce, kliknij w tytuł — przejdziesz na stronę detali. Klasy CSS znasz z Lab 5: na listingu `.book`, `h2.title`, `.author`, `.price`, `a.book-link`, `a.next-page`; na detalach `h1.title`, `.description`, `.stock`.

## Zadanie

Wygeneruj spidera i napisz go od zera:

```bash
scrapy genspider books 127.0.0.1
```

Wymagania:

1. Start od `http://127.0.0.1:5000/books`.
2. `parse` dla każdej książki na listingu podąża na jej stronę detali (callback wyciągający dane), a po linku `a.next-page` przechodzi na kolejną stronę listingu (callback `self.parse`).
3. Drugi callback generuje słownik z polami: `title`, `author`, `description`, `price`, `stock`.
4. Eksport do `bookshop.json`.

```bash
scrapy crawl books -O bookshop.json
```

::: {.callout-tip}
## Eksploruj selektory w shellu
Zanim napiszesz spidera, otwórz `scrapy shell "http://127.0.0.1:5000/books"` i sprawdź: `response.css("a.book-link::attr(href)").getall()`, `response.css("a.next-page::attr(href)").get()`. Potem shell na stronie detali: `response.css("h1.title::text").get()` itd. `response.follow` przyjmuje także obiekt `<a>` wprost — wyciągnie z niego `href` sam.
:::

::: {.callout-note}
## Checkpoint
1. Ile książek zebrał spider? Czy zgadza się z liczbą z `bookshop.json` z Lab 5?
2. Czy każdy rekord ma pola `title`, `author`, `description`, `price`, `stock`?
3. **Test regresji**: porównaj dane (posortowane po `title`) z `bookshop.json` z Lab 5/6. Powinny być identyczne — ta sama strona, inne narzędzie, ten sam wynik. Jeśli się różnią, gdzieś jest błąd w selektorze.
4. Czy spider zatrzymał się sam (nie zapętlił)? Scrapy deduplikuje URL-e, więc nawet gdy ostatnia strona linkuje wstecz, nie pobierze jej ponownie.
:::

---

# Ćwiczenie 2: spider Collatza — łańcuch

Miasta to katalog z paginacją, bookshop to lista → detal. Trzeci kształt: **łańcuch**. Serwer Collatza z Wykładu 2 generuje po jednej liczbie na stronę, a link prowadzi do następnej liczby w ciągu. Ręcznego crawlera dla niego pisałeś na Labie 4 (Ćwiczenie A). Teraz wersja w Scrapy — bez szkieletu.

## Serwer

Zatrzymaj poprzedni serwer (`Ctrl+C`). W `lab11/` utwórz `collatz_app.py` (kod z Wykładu 2):

```python
from flask import Flask

app = Flask(__name__)


@app.route("/collatz/<int:n>")
def collatz(n):
    if n == 1:
        return """
        <html><body>
            <h1>1</h1>
            <p>Koniec ciągu!</p>
            <a href="/collatz/7">Rozpocznij od 7</a>
        </body></html>
        """

    if n % 2 == 0:
        next_n = n // 2
    else:
        next_n = 3 * n + 1

    return f"""
    <html><body>
        <h1>{n}</h1>
        <p>Następna liczba: {next_n}</p>
        <a href="/collatz/{next_n}">Przejdź do {next_n}</a>
        <br>
        <a href="/collatz/1">Idź do 1 (koniec)</a>
    </body></html>
    """
```

Uruchom go w **Terminalu 1**:

```bash
flask --app collatz_app run --debug -p 5000
```

Sprawdź w przeglądarce `http://127.0.0.1:5000/collatz/27` — przeklikaj kilka kroków „Przejdź do …".

## Zadanie

Wygeneruj spidera `collatz` i napisz go samodzielnie:

```bash
scrapy genspider collatz 127.0.0.1
```

Wymagania:

1. Start od `http://127.0.0.1:5000/collatz/27`.
2. Na każdej stronie wygeneruj `{"n": <liczba z nagłówka h1>}`.
3. Podążaj za linkiem do następnej liczby. Gdy go nie ma — koniec.
4. Eksport do `collatz_27.json`.

```bash
scrapy crawl collatz -O collatz_27.json
```

::: {.callout-warning}
## Na stronie są DWA linki `/collatz/...`
Każda strona ma „Przejdź do {next_n}" **oraz** „Idź do 1 (koniec)". Naiwne `response.css("a::attr(href)").get()` może złapać niewłaściwy — spider skoczyłby prosto do `/collatz/1` i crawl skończyłby się po jednym kroku. Wybierz link precyzyjnie. Na stronie końcowej (`n = 1`) jest tylko „Rozpocznij od 7" — i właśnie za nim **nie** chcesz podążać, inaczej spider wpadnie w nieskończoną pętlę 7 → … → 1 → 7. (Z `n = 27` ciąg ma 112 kroków — tyle rekordów powinno być w pliku.)
:::

::: {.callout-tip}
## Dlaczego Collatz nie zrównolegli się jak miasta
Przy miastach Scrapy pobierał strony współbieżnie — wszystkie linki „Następna" wpadały do kolejki niemal naraz. Collatz jest inny: nie znasz następnego URL-a, póki nie pobierzesz bieżącej strony. To **zależność sekwencyjna** — kolejka nigdy nie ma więcej niż jednego oczekującego żądania, więc współbieżność Scrapy nic tu nie przyspiesza. Framework daje moc, ale nie wyczaruje jej z łańcucha, w którym każdy krok zależy od poprzedniego.
:::

::: {.callout-note}
## Checkpoint
1. Czy `collatz_27.json` ma 112 rekordów? Czy zaczyna się od 27, a kończy na 1?
2. Czy spider zatrzymał się sam, czy musiałeś go ubić (`Ctrl+C`)? Jeśli to drugie — najpewniej podążasz za linkiem „Rozpocznij od 7" ze strony końcowej.
3. Porównaj z `collatz_27.json` z Lab 4 — ten sam ciąg? Tu kolejność **powinna** być zachowana (w odróżnieniu od miast) — wyjaśnij dlaczego.
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

## Ćwiczenie B (opcjonalne): spider na serwer szczytów

Na Labie 4 (Ćwiczenie 2) zbudowałeś serwer `/peaks` — katalog polskich szczytów z paginacją (klucze `name`, `height`, `range`). Uruchom go i napisz spidera `peaks`.

To samo zadanie co miasta, tylko inny cel i nazwy pól — logika spidera (paginacja przez `response.follow`, `yield dict`) jest identyczna. Punkt wyjścia: skopiuj `cities.py`, zmień `name`, `start_urls`, selektory i klucze. Wynik: `peaks.json` z 20 szczytami.

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
`response.css(...)` i `response.xpath(...)` działają na tym samym obiekcie — możesz je nawet łączyć (`response.css("div.book").xpath('./h2/text()')`). Zadania 1–4 są wygodniejsze w CSS, zadanie 5 (nawigacja osią) — w XPath.
:::

---

# Podsumowanie

W tym labie:

* utworzyłeś projekt Scrapy (`startproject`, `genspider`) i poznałeś role plików — dotykaliśmy tylko `spiders/`,
* używałeś `scrapy shell` do sprawdzania selektorów na żywo, zanim trafiły do spidera,
* przepisałeś crawler miast z Lab 4 na spidera — to samo zadanie, ten sam wynik, kilkanaście linii zamiast pętli z ręcznym pobieraniem, budowaniem URL-i i zapisem,
* napisałeś — bez szkieletu — spidera bookshop w układzie **lista → detal** (`parse` + drugi callback) oraz spidera Collatza dla **łańcucha** stron,
* zobaczyłeś, że Scrapy pobiera współbieżnie, więc paginacja miesza kolejność wyników, a łańcuch zależny (Collatz) i tak biegnie sekwencyjnie,
* eksportowałeś wyniki do JSON, CSV i JSON Lines jednym przełącznikiem `-O`.

Trzy kształty stron, jeden wzorzec spidera:

| Kształt | Strona | Nawigacja w `parse` |
|---|---|---|
| Katalog z paginacją | miasta (Lab 4) | jeden link „Następna" → `self.parse` |
| Lista → detal | bookshop (Lab 5–6) | wiele linków → callback detalu **+** „Następna" → `self.parse` |
| Łańcuch | Collatz (Wykład 2 / Lab 4) | jeden link do następnej → `self.parse` |

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