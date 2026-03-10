---
title: "Wykład 3: HTML jako drzewo — selekcja danych"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

## Cele i zakres

Dane z surowego HTML można pozyskiwać, korzystając z wyrażeń regularnych i metod na łańcuchach znaków. Na dłuższą metę jest to jednak niewygodne i podatne na błędy. Teraz omówimy bardziej specjalistyczne narzędzia — parsery HTML, które rozumieją strukturę dokumentu i budują na jej podstawie drzewo obiektów.

Zakres obejmuje:

* HTML jako drzewo — struktura dokumentu, model DOM,
* BeautifulSoup — nawigacja po drzewie i wyszukiwanie elementów,
* selektory CSS — zwięzły język zapytań do drzewa HTML,
* XPath — najpotężniejszy mechanizm selekcji: osie, predykaty, funkcje,
* porównanie trzech metod na tych samych danych.

---

## Od tekstu do drzewa

### Dlaczego nie regex

Dane z HTML można wyciągać, używając wyrażeń regularnych lub metod na stringach (`split`, `index`, itd.). To podejście działa, gdy HTML jest prosty i przewidywalny — np. własny serwer Flask z prostymi szablonami. Jednak w realnym świecie HTML jest często złożony, nieuporządkowany i pełen wyjątków. Regex szybko staje się nieczytelny i podatny na błędy.

Rozważmy fragment:

```html
<a href="/page/1">Strona 1</a>
<a href="/page/2" class="active">Strona 2</a>
<!-- <a href="/page/old">stary link</a> -->
<a href = "/page/3" >Strona 3</a>
```

Regex `href="([^"]+)"` znajdzie też link z komentarza. Nie poradzi sobie ze spacjami wokół `=` w ostatniej linii. Przy bardziej złożonym HTML — zagnieżdżonych tabelach, atrybutach z cudzysłowami, warunkowych komentarzach — wyrażenia regularne stają się nieczytelne i błędogenne.

Rozwiązanie: **parser HTML**, który rozumie strukturę dokumentu i buduje z tekstu **drzewo**, po którym możemy nawigować.

### HTML — przypomnienie składni

**Tag** (element) to podstawowa jednostka HTML:

```html
<a href="/next" class="link">Kliknij</a>
```

* `a` — nazwa tagu,
* `href="/next"`, `class="link"` — **atrybuty** (pary klucz–wartość),
* `Kliknij` — **zawartość tekstowa** (text content),
* `</a>` — tag zamykający.

**Zagnieżdżenie** tworzy hierarchię:

```html
<div>
  <h1>Tytuł</h1>
  <ul>
    <li>Element 1</li>
    <li>Element 2</li>
  </ul>
</div>
```

`<div>` zawiera `<h1>` i `<ul>`, a `<ul>` zawiera dwa `<li>`. To jest **drzewo**.

### Model drzewa (DOM)

Każdy dokument HTML ma strukturę drzewa. Powyższy fragment wygląda tak:

```
div
├── h1
│   └── "Tytuł"
├── ul
│   ├── li
│   │   └── "Element 1"
│   └── li
│       └── "Element 2"
```

Terminologia:

* **korzeń** (root) — najwyższy element (tu: `div`),
* **dziecko** (child) — element bezpośrednio zagnieżdżony (`h1` jest dzieckiem `div`),
* **potomek** (descendant) — element na dowolnym poziomie zagnieżdżenia (`li` jest potomkiem `div`, ale nie dzieckiem),
* **rodzic** (parent) — element nadrzędny (`ul` jest rodzicem `li`),
* **rodzeństwo** (sibling) — elementy na tym samym poziomie (`h1` i `ul` są rodzeństwem).

Parser HTML (np. BeautifulSoup, lxml) zamienia surowy tekst na takie drzewo. Od tego momentu nie operujemy na stringach — operujemy na **węzłach drzewa**, które mają rodziców, dzieci, atrybuty i tekst.

---

## BeautifulSoup — nawigacja po drzewie

### Instalacja i parsowanie

```bash
pip install beautifulsoup4
```

```python
from bs4 import BeautifulSoup

html = """
<html>
<body>
  <h1>Produkty</h1>
  <table class="data">
    <tr><th>Nazwa</th><th>Cena</th></tr>
    <tr><td>Jabłko</td><td class="price">3.50</td></tr>
    <tr><td>Gruszka</td><td class="price">4.20</td></tr>
    <tr><td>Śliwka</td><td class="price">5.00</td></tr>
  </table>
  <a href="/page/2">Następna strona</a>
</body>
</html>
"""

soup = BeautifulSoup(html, "html.parser")
```

`BeautifulSoup(html, "html.parser")` parsuje tekst i zwraca obiekt reprezentujący korzeń drzewa. `"html.parser"` to parser z biblioteki standardowej Pythona — nie wymaga dodatkowych instalacji.

### Wyszukiwanie elementów: `find` i `find_all`

**`find(tag, attrs)`** — zwraca **pierwszy** pasujący element (lub `None`):

```python
h1 = soup.find("h1")
print(h1.text)  # "Produkty"
```

**`find_all(tag, attrs)`** — zwraca **listę** wszystkich pasujących:

```python
rows = soup.find_all("tr")
print(len(rows))  # 4 (nagłówek + 3 wiersze danych)
```

Pierwszy argument może być też **listą tagów** — wtedy `find_all` zwraca elementy pasujące do dowolnego z nich:

```python
# Wszystkie nagłówki h1, h2 i h3 w dokumencie
headers = soup.find_all(["h1", "h2", "h3"])

# Wszystkie linki: zarówno <a> jak i <link>
all_links = soup.find_all(["a", "link"])
```

### Filtrowanie po atrybutach

Atrybuty podajemy jako argumenty nazwane:

```python
# Wszystkie td z klasą "price"
prices = soup.find_all("td", class_="price")
for td in prices:
    print(td.text)  # 3.50, 4.20, 5.00
```

Uwaga: `class` jest słowem kluczowym Pythona, dlatego BeautifulSoup używa `class_` (z podkreśleniem).

```python
# Wszystkie linki (tagi <a> z atrybutem href)
links = soup.find_all("a", href=True)
for a in links:
    print(a["href"], a.text)  # /page/2 Następna strona
```

`href=True` oznacza: „tag musi mieć atrybut `href`" (dowolna wartość).

### Wyciąganie danych z elementu

Każdy znaleziony element to obiekt `Tag` z atrybutami:

* `.text` / `.get_text()` — zawartość tekstowa (rekurencyjnie, ze wszystkich potomków),
* `.string` — tekst, tylko jeśli element ma dokładnie jedno dziecko tekstowe,
* `["atrybut"]` — wartość atrybutu (rzuca `KeyError`, jeśli brak),
* `.get("atrybut", domyślna)` — wartość atrybutu (bezpieczna wersja),
* `.attrs` — słownik wszystkich atrybutów,
* `.name` — nazwa tagu (np. `"td"`, `"a"`).

```python
link = soup.find("a", href=True)
print(link.name)            # "a"
print(link["href"])         # "/page/2"
print(link.get("class"))   # None (brak klasy)
print(link.text)            # "Następna strona"
```

### Nawigacja po drzewie

Oprócz wyszukiwania (`find`, `find_all`) można nawigować po relacjach rodzic–dziecko–rodzeństwo:

```python
table = soup.find("table", class_="data")

# Dzieci (bezpośrednie)
for child in table.children:
    if child.name:  # pomijamy białe znaki (NavigableString)
        print(child.name)  # "tr", "tr", "tr", "tr"

# Rodzic
first_td = soup.find("td")
print(first_td.parent.name)  # "tr"

# Rodzeństwo
first_row = table.find("tr")
second_row = first_row.find_next_sibling("tr")
print(second_row.text)  # "Jabłko3.50"
```

Nawigacja jest przydatna, gdy struktura jest regularna i chcemy „przeskoczyć" do sąsiedniego elementu — np. znaleźć komórkę obok nagłówka.

### Pełny przykład: ekstrakcja tabeli

Łączymy powyższe techniki w kompletny wzorzec:

```python
table = soup.find("table", class_="data")
rows = table.find_all("tr")

# Pomijamy wiersz nagłówkowy (pierwszy tr)
for row in rows[1:]:
    cells = row.find_all("td")
    name = cells[0].text
    price = cells[1].text
    print(f"  {name}: {price} zł")
```

Wynik:

```
  Jabłko: 3.50 zł
  Gruszka: 4.20 zł
  Śliwka: 5.00 zł
```

To jest wzorzec, który będzie się powtarzał: **znajdź kontener → iteruj po elementach → wyciągnij dane z każdego**. Zmienia się selektor i struktura — logika pozostaje ta sama.

---

## Selektory CSS

### Po co kolejna metoda

`find_all("td", class_="price")` działa, ale przy bardziej złożonych strukturach staje się rozwlekły. Selektory CSS to **zwięzły język zapytań** do drzewa HTML — ten sam, którego używa przeglądarka do stosowania stylów. W DevTools (F12 → Elements → prawy klik → Copy selector).

W BeautifulSoup selektory CSS są dostępne przez metody `select` i `select_one`.

### Składnia selektorów — minimum do pracy

**Selektor typu** — nazwa tagu:

```python
soup.select("p")         # wszystkie <p>
soup.select("a")         # wszystkie <a>
```

**Selektor klasy** — `.nazwaklasy`:

```python
soup.select(".price")    # wszystkie elementy z class="price"
```

**Selektor ID** — `#identyfikator`:

```python
soup.select("#main")     # element z id="main"
```

**Selektor atrybutu** — `[atrybut]` lub `[atrybut=wartość]`:

```python
soup.select("[href]")              # elementy z atrybutem href
soup.select('[data-type="csv"]')   # elementy z data-type="csv"
```

**Potomek** — spacja między selektorami:

```python
soup.select("table td")           # wszystkie <td> wewnątrz <table> (dowolna głębokość)
```

**Dziecko bezpośrednie** — `>`:

```python
soup.select("ul > li")            # <li> będące bezpośrednimi dziećmi <ul>
```

**Kombinacja selektorów:**

```python
soup.select("table.data td.price")  # <td class="price"> wewnątrz <table class="data">
```

Czytamy od lewej do prawej: „znajdź `<table>` z klasą `data`, a w nim wszystkie `<td>` z klasą `price`".

### Pseudoklasy

**`:first-child`** — pierwszy element wśród rodzeństwa:

```python
soup.select("tr:first-child")     # pierwszy <tr> w każdym rodzicu
```

**`:nth-child(n)`** — n-ty element (numeracja od 1):

```python
soup.select("tr:nth-child(2)")    # drugi <tr> (pierwszy wiersz danych, jeśli pierwszy to nagłówek)
```

**`:not(selektor)`** — wykluczenie:

```python
soup.select("td:not(.price)")     # <td> bez klasy "price"
```

### `select` i `select_one`

```python
# Lista wyników (jak find_all)
cells = soup.select("table.data td.price")
for td in cells:
    print(td.text)

# Pierwszy wynik (jak find)
link = soup.select_one("a[href]")
print(link["href"])
```

### Porównanie: `find_all` vs `select`

To samo zadanie — wyciągnięcie cen z tabeli:

```python
# BeautifulSoup API
prices = soup.find_all("td", class_="price")

# Selektory CSS
prices = soup.select("td.price")
```

Efekt identyczny. Selektor CSS jest krótszy. Przy bardziej złożonych zapytaniach różnica rośnie:

```python
# Wszystkie linki wewnątrz div-a z id="nav", które mają klasę "active"
# BeautifulSoup API:
div = soup.find("div", id="nav")
links = div.find_all("a", class_="active") if div else []

# Selektory CSS:
links = soup.select("div#nav a.active")
```

Jedna linia zamiast dwóch, bez warunku `if div`.

---

## XPath

### Dlaczego jeszcze jedna metoda

Selektory CSS są zwięzłe, ale mają ograniczenia. Nie potrafią:

* selekcjonować po **zawartości tekstowej** elementu (np. „znajdź `<a>`, którego tekst zawiera słowo «Następna»"),
* poruszać się **w górę** drzewa (od dziecka do rodzica),
* wybierać **rodzeństwa** w określonym kierunku (np. „element bezpośrednio po nagłówku"),
* stosować **warunków arytmetycznych** (np. „wiersze o indeksie > 1").

**XPath** to język zapytań do dokumentów XML/HTML, który to wszystko potrafi. Jest standardem W3C — używany w Scrapy, `lxml`, narzędziach do testowania (Selenium) i przetwarzaniu XML.

### Narzędzie: `lxml`

BeautifulSoup nie obsługuje XPath. Do tego potrzebujemy biblioteki `lxml`:

```bash
pip install lxml
```

```python
from lxml import etree

html = """
<html>
<body>
  <h1>Produkty</h1>
  <table class="data">
    <tr><th>Nazwa</th><th>Cena</th></tr>
    <tr><td>Jabłko</td><td class="price">3.50</td></tr>
    <tr><td>Gruszka</td><td class="price">4.20</td></tr>
    <tr><td>Śliwka</td><td class="price">5.00</td></tr>
  </table>
  <a href="/page/2">Następna strona</a>
</body>
</html>
"""

tree = etree.HTML(html)
```

`etree.HTML(html)` parsuje tekst HTML i zwraca korzeń drzewa. Metoda `.xpath(wyrażenie)` zwraca listę wyników.

### Ścieżki: absolutne i względne

**Ścieżka absolutna** — od korzenia, przez kolejne poziomy:

```python
tree.xpath("/html/body/h1")           # [<Element h1>]
tree.xpath("/html/body/table/tr/td")  # wszystkie <td> w tabeli
```

**Ścieżka względna** — `//` oznacza „gdziekolwiek w drzewie":

```python
tree.xpath("//h1")            # wszystkie <h1> w dokumencie
tree.xpath("//td")            # wszystkie <td> w dokumencie
```

W praktyce prawie zawsze używamy `//` — ścieżki absolutne są niestabilne (zmieniają się, gdy zmieni się struktura strony).

### Predykaty — filtrowanie wyników

Predykaty w nawiasach kwadratowych `[]` filtrują wyniki:

**Po atrybucie:**

```python
tree.xpath('//td[@class="price"]')    # <td> z class="price"
tree.xpath('//a[@href]')              # <a> z atrybutem href
```

**Po pozycji:**

```python
tree.xpath('//tr[1]')          # pierwszy <tr> (XPath liczy od 1)
tree.xpath('//tr[position()>1]')  # wszystkie <tr> oprócz pierwszego
tree.xpath('//tr[last()]')     # ostatni <tr>
```

**Po tekście:**

```python
tree.xpath('//a[text()="Następna strona"]')           # <a> z dokładnym tekstem
tree.xpath('//a[contains(text(),"Następna")]')         # <a> z tekstem zawierającym "Następna"
tree.xpath('//td[contains(@class,"price")]')           # <td> z klasą zawierającą "price"
```

Selekcja po tekście to coś, czego CSS selektory **nie potrafią**. W scrapingu jest przydatna — np. „znajdź link z napisem «Następna strona»" bez znajomości jego `href`.

### Wyciąganie danych

XPath może zwracać **elementy** lub **wartości** (teksty, atrybuty):

```python
# Elementy
elements = tree.xpath('//td[@class="price"]')
for el in elements:
    print(el.text)  # "3.50", "4.20", "5.00"

# Bezpośrednio tekst
texts = tree.xpath('//td[@class="price"]/text()')
print(texts)  # ["3.50", "4.20", "5.00"]

# Bezpośrednio atrybuty
hrefs = tree.xpath('//a/@href')
print(hrefs)  # ["/page/2"]
```

Różnica: `//td[@class="price"]` zwraca listę obiektów `Element`, a `//td[@class="price"]/text()` zwraca listę stringów. Analogicznie `//a/@href` zwraca wartości atrybutu, nie elementy.

### Osie — poruszanie się w wielu kierunkach

Domyślna oś to `child` — schodzenie w dół drzewa. XPath oferuje wiele osi, z których najważniejsze to:

**`parent`** — rodzic elementu:

```python
# Znajdź <tr> będący rodzicem <td> z ceną "5.00"
tree.xpath('//td[text()="5.00"]/parent::tr')
```

Skrót: `..` oznacza `parent::node()`:

```python
tree.xpath('//td[text()="5.00"]/..')  # to samo
```

**`following-sibling`** — rodzeństwo po bieżącym elemencie:

```python
# Znajdź <td>, które jest rodzeństwem <td> z tekstem "Jabłko"
tree.xpath('//td[text()="Jabłko"]/following-sibling::td')
# → [<td class="price">3.50</td>]
```

To jest potężny wzorzec: „mam komórkę z nazwą — daj mi komórkę obok z ceną". CSS selektory nie mają odpowiednika.

**`preceding-sibling`** — rodzeństwo przed bieżącym elementem:

```python
# Cena "4.20" — jaka jest nazwa tego produktu?
tree.xpath('//td[text()="4.20"]/preceding-sibling::td')
# → [<td>Gruszka</td>]
```

**`ancestor`** — przodkowie (rodzic, dziadek, itd.):

```python
# Znajdź <table> będący przodkiem <td> z klasą "price"
tree.xpath('//td[@class="price"]/ancestor::table')
```

### Kombinowanie predykatów i osi

XPath pozwala budować złożone zapytania:

```python
# Wiersze tabeli "data", które zawierają cenę > 4.00
# (XPath porównuje tekstowo, ale number() konwertuje)
tree.xpath('//table[@class="data"]//tr[td[@class="price" and number(text()) > 4.0]]')
```

To jest zapytanie, którego nie da się wyrazić jednym selektorem CSS.

### Pełny przykład: ekstrakcja tabeli z lxml

```python
from lxml import etree

tree = etree.HTML(html)

# Pomijamy nagłówek: tr[position()>1]
rows = tree.xpath('//table[@class="data"]//tr[position()>1]')

for row in rows:
    name = row.xpath('td[1]/text()')[0]
    price = row.xpath('td[2]/text()')[0]
    print(f"  {name}: {price} zł")
```

Wynik identyczny jak w wersji BeautifulSoup. Różnica: XPath robi selekcję i filtrowanie (pominięcie nagłówka) w jednym wyrażeniu.

---

## Trzy metody — porównanie

To samo zadanie — wyciągnięcie cen z tabeli o klasie `data` — rozwiązane trzema sposobami:

**BeautifulSoup API:**

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
for td in soup.find_all("td", class_="price"):
    print(td.text)
```

**Selektory CSS (w BeautifulSoup):**

```python
for td in soup.select("table.data td.price"):
    print(td.text)
```

**XPath (lxml):**

```python
from lxml import etree

tree = etree.HTML(html)
for price in tree.xpath('//table[@class="data"]//td[@class="price"]/text()'):
    print(price)
```

Zestawienie:

| Metoda | Narzędzie | Mocna strona | Ograniczenie |
|---|---|---|---|
| API BeautifulSoup | `find` / `find_all` | Intuicyjne, pythonowe API | Rozwlekłe przy złożonych zapytaniach |
| Selektory CSS | `select` / `select_one` | Zwięzłe, znane z przeglądarki | Brak selekcji po tekście, brak osi w górę |
| XPath | `lxml` + `xpath()` | Najpotężniejsze: osie, predykaty, funkcje | Składnia mniej intuicyjna na początku |

W praktyce wybór zależy od zadania:

* **Proste ekstrakcje** (lista linków, komórki tabeli) — CSS selektory wystarczą i są najkrótsze.
* **Nawigacja po relacjach** (komórka obok nagłówka, rodzic elementu) — XPath z osiami.
* **Szybkie prototypowanie** w konsoli — `find` / `find_all`, bo nie trzeba pamiętać składni.
* **Scrapy** (Wykład 6) — wspiera zarówno CSS, jak i XPath natywnie.

Nie trzeba wybierać jednej metody. W jednym projekcie można używać CSS do prostych rzeczy i XPath tam, gdzie potrzebna jest większa precyzja.

---

## DevTools — selektor prosto z przeglądarki

Przeglądarki (Chrome, Firefox) mają wbudowane narzędzia, które pomagają budować selektory:

1. Otwórz stronę w przeglądarce.
2. Kliknij prawym przyciskiem na interesujący element → **Zbadaj** (Inspect).
3. W panelu Elements kliknij prawym na podświetlony tag → **Copy** → **Copy selector** lub **Copy XPath**.

Przeglądarka wygeneruje selektor wskazujący na ten konkretny element. Wygenerowane selektory bywają jednak zbyt specyficzne — zawierają długie ścieżki i indeksy, np.:

```
#page > div:nth-child(3) > table > tbody > tr:nth-child(2) > td:nth-child(2)
```

To działa na jednym elemencie, ale nie uogólnia się na „wszystkie ceny w tabeli". Dlatego DevTools traktujemy jako **punkt startowy** — podpowiedź, nie gotowe rozwiązanie. Selektor produkcyjny piszemy ręcznie, tak żeby wyciągał **klasę danych**, nie jeden konkretny element.

---

## Uwagi praktyczne

### Parser: `html.parser` vs `lxml`

BeautifulSoup obsługuje kilka parserów:

* `"html.parser"` — z biblioteki standardowej, wystarczający w większości przypadków,
* `"lxml"` — szybszy, lepiej radzi sobie z uszkodzonym HTML-em.

W labach używamy `"html.parser"` (zero dodatkowych zależności dla BeautifulSoup). Osobno importujemy `lxml.etree` do XPath.

### Kodowanie znaków

HTML z serwera przychodzi jako odpowiedź HTTP. Biblioteka `requests` automatycznie dekoduje tekst (na podstawie nagłówka `Content-Type` i detekcji). Dlatego `r.text` zwraca gotowy `str`, który można od razu podać do BeautifulSoup:

```python
r = requests.get("http://localhost:5000/page")
soup = BeautifulSoup(r.text, "html.parser")
```

Dla `lxml`:

```python
tree = etree.HTML(r.text)
```

### Biały tekst i `.text` vs `.get_text(strip=True)`

`.text` zwraca cały tekst z elementu i jego potomków — łącznie z białymi znakami (wcięcia, newline). `.get_text(strip=True)` usuwa białe znaki z początku i końca każdego fragmentu:

```python
cell = soup.find("td")
print(repr(cell.text))                    # "\n    Jabłko\n  "
print(repr(cell.get_text(strip=True)))    # "Jabłko"
```

W scrapingu prawie zawsze chcemy `strip=True` lub ręczny `.strip()`.

---

## Podsumowanie

Na tym wykładzie:

* zobaczyliśmy, że regex jest niewygodny w podczas przeszukiwania HTML — i zastąpiliśmy go parserem, który buduje drzewo,
* poznaliśmy BeautifulSoup: `find`, `find_all`, nawigację po drzewie (rodzic, dzieci, rodzeństwo),
* nauczyliśmy się selektorów CSS: zwięzła składnia do prostych i średnio złożonych zapytań,
* wprowadziliśmy XPath jako najpotężniejsze narzędzie selekcji: predykaty, selekcja po tekście, osie (`following-sibling`, `parent`, `ancestor`),
* porównaliśmy trzy metody na tych samych danych i zobaczyliśmy, kiedy która jest najlepsza.

**Co dalej:**

* **Lab 5**: BeautifulSoup + selektory CSS — parsowanie stron z lokalnego serwera Flask (tabele, listy, zagnieżdżone struktury). 
* **Lab 6**: XPath na tych samych stronach — porównanie trzech metod, trudniejsze przypadki: osie (`following-sibling`, `ancestor`), predykaty pozycyjne i tekstowe.