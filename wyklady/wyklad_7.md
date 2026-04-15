---
title: "Wykład 7: Strony dynamiczne — JavaScript, AJAX, Selenium"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

## Cele i zakres

Dotychczasowe narzędzia — `requests`, BeautifulSoup, Scrapy — działały na HTML zwróconym przez serwer. Wysyłaliśmy żądanie HTTP, dostawaliśmy dokument HTML, parsowaliśmy go i wyciągaliśmy dane. Ten model zakładał, że **wszystkie dane są obecne w HTML już w momencie odpowiedzi serwera**. Coraz więcej stron tak nie działa. Serwer wysyła szkielet HTML z kodem JavaScript, a dopiero przeglądarka — po odebraniu dokumentu — uruchamia ten kod, który pobiera dane z serwera i wstawia je do strony. `requests` nie jest przeglądarką, nie wykonuje JavaScriptu, więc widzi pusty szkielet.

Ten wykład pokazuje, jak rozpoznać taki scenariusz i jak sobie z nim radzić.

Zakres obejmuje:

* problem: dlaczego `requests` czasem „nie widzi" danych,
* diagnostyka: DevTools → Network → XHR/Fetch — jak znaleźć ukryte API,
* AJAX shortcut: bezpośrednie odpytanie API z poziomu `requests`,
* Selenium: sterowanie przeglądarką, gdy shortcut nie istnieje,
* drzewo decyzyjne — dobór narzędzia do problemu.

---

## Problem: `requests` nie widzi danych

### Model z Wykładu 1 — przypomnienie

Na Wykładzie 1 opisaliśmy cykl żądanie–odpowiedź:

1. Klient wysyła żądanie HTTP (`GET /page`).
2. Serwer przetwarza żądanie i zwraca odpowiedź — dokument HTML.
3. Klient (przeglądarka, `requests`, Scrapy) odbiera dokument.

W tym modelu **dane są w HTML**. Dokument, który dostajemy od serwera, zawiera wszystkie teksty, linki, tabele — gotowe do parsowania. Tak działały strony z naszych serwerów Flask i tak działał `books.toscrape.com`.

### Nowy aktor: JavaScript w przeglądarce

Wiele współczesnych stron działa inaczej. Serwer wysyła **szkielet HTML** — sam układ strony, menu, nagłówki — ale bez właściwych danych. W szkielecie jest za to kod JavaScript, który:

1. uruchamia się **w przeglądarce**, po odebraniu dokumentu,
2. wysyła **własne żądania HTTP** do serwera (po dane),
3. otrzymuje dane (zwykle JSON),
4. wstawia je do strony — modyfikując DOM.

Z perspektywy użytkownika wygląda to tak samo: strona się ładuje i po chwili pojawiają się dane. Ale z perspektywy `requests` sytuacja jest zupełnie inna — `requests` nie jest przeglądarką. Nie uruchamia JavaScriptu. Dostaje szkielet HTML i na tym kończy.

### Demo: `quotes.toscrape.com/scroll`

Strona `quotes.toscrape.com/scroll` wyświetla cytaty ładowane dynamicznie — w miarę przewijania strony JavaScript pobiera kolejne porcje danych z serwera.

Spróbujmy pobrać ją za pomocą `requests`:

```python
import requests

r = requests.get("https://quotes.toscrape.com/scroll")
print(r.status_code)  # 200
print(len(r.text))    # kilka KB
```

Status 200, odpowiedź niepusta — wygląda normalnie. Ale szukając cytatów:

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(r.text, "html.parser")
quotes = soup.select("div.quote")
print(len(quotes))  # 0
```

Zero cytatów. Strona odpowiedziała poprawnie, ale HTML, który dostaliśmy, to **szkielet bez danych**. Cytaty zostaną pobrane i wstawione dopiero po uruchomieniu JavaScriptu — a `requests` tego nie robi.

To jest punkt wyjścia: musimy albo znaleźć sposób na dotarcie do danych bez przeglądarki, albo użyć narzędzia, które przeglądarkę uruchomi.

---

## Diagnostyka: DevTools i zakładka Network

### Gdzie JavaScript bierze dane?

Skoro JavaScript pobiera dane z serwera, to robi to za pomocą zwykłych żądań HTTP — tyle że wysyłanych z poziomu przeglądarki, nie z naszego kodu. Te żądania można zobaczyć w narzędziach deweloperskich przeglądarki (DevTools).

Procedura:

1. Otwieramy `https://quotes.toscrape.com/scroll` w przeglądarce (Chrome lub Firefox).
2. Otwieramy DevTools: `F12` (lub `Ctrl+Shift+I`).
3. Przechodzimy do zakładki **Network**.
4. W filtrze wybieramy **Fetch/XHR** — pokazuje tylko żądania wysyłane przez JavaScript (AJAX).
5. Przewijamy stronę w dół.

Po przewinięciu pojawiają się żądania do:

```
https://quotes.toscrape.com/api/quotes?page=1
https://quotes.toscrape.com/api/quotes?page=2
https://quotes.toscrape.com/api/quotes?page=3
...
```

Klikając na dowolne z nich i sprawdzając zakładkę **Response**, widzimy JSON z cytatami:

```json
{
  "has_next": true,
  "page": 1,
  "quotes": [
    {
      "author": {"name": "Albert Einstein", "goodreads_link": "..."},
      "tags": ["change", "deep-thoughts", "thinking", "world"],
      "text": "\u201cThe world as we have created it is a process of our thinking..."
    },
    ...
  ]
}
```

Dane są tu — po prostu nie w HTML, lecz w osobnym endpoincie JSON, który JavaScript odpytuje w tle.

### AJAX shortcut

Skoro znamy URL API, nie potrzebujemy ani JavaScriptu, ani przeglądarki. Możemy odpytać ten endpoint bezpośrednio z `requests`:

```python
import requests

r = requests.get("https://quotes.toscrape.com/api/quotes?page=1")
data = r.json()

print(data["page"])       # 1
print(data["has_next"])   # True
print(len(data["quotes"]))  # 10

for q in data["quotes"]:
    print(f'{q["author"]["name"]}: {q["text"][:50]}...')
```

To działa, bo endpoint API jest publiczny i nie wymaga żadnych tokenów ani sesji. Możemy iterować po stronach tak samo jak w Labach 1–2:

```python
import requests

all_quotes = []
page = 1

while True:
    r = requests.get(f"https://quotes.toscrape.com/api/quotes?page={page}")
    data = r.json()
    all_quotes.extend(data["quotes"])
    if not data["has_next"]:
        break
    page += 1

print(f"Zebrano {len(all_quotes)} cytatów")  # 100
```

To jest **AJAX shortcut**: zamiast uruchamiać przeglądarkę i symulować przewijanie, odpytujemy API bezpośrednio. Jest to szybsze, prostsze i nie wymaga dodatkowych narzędzi.

### Kiedy shortcut nie działa

Nie zawsze jest to możliwe:

* endpoint API może wymagać tokenu lub sesji, których nie da się łatwo odtworzyć,
* dane mogą być generowane po stronie klienta (np. obliczenia w JavaScript),
* strona może nie mieć osobnego API — JavaScript może otrzymywać dane osadzone w HTML lub renderowane z szablonu po stronie klienta.

W tych przypadkach potrzebujemy narzędzia, które uruchomi prawdziwą przeglądarkę.

---

## Selenium: sterowanie przeglądarką z Pythona

### Czym jest Selenium

Selenium to biblioteka, która pozwala programowo sterować przeglądarką — otwierać strony, klikać elementy, wypełniać formularze, przewijać i czytać zawartość strony **po wykonaniu JavaScriptu**. Przeglądarka uruchamiana przez Selenium jest prawdziwą przeglądarką (Chrome, Firefox) — wykonuje JavaScript, renderuje stronę, obsługuje AJAX — dokładnie tak, jak gdyby siedział przed nią użytkownik.

### Instalacja

Selenium wymaga dwóch elementów: biblioteki Pythona i sterownika przeglądarki (ChromeDriver). Pakiet `webdriver-manager` automatyzuje pobieranie sterownika:

```bash
pip install selenium webdriver-manager
```

`webdriver-manager` pobiera odpowiednią wersję ChromeDriver z sieci przy pierwszym uruchomieniu. W środowisku laboratoryjnym (GoBack) instalację powtarzamy przy każdej sesji — tak samo jak przy Scrapy.

### Otwarcie strony i ekstrakcja elementów

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

driver.get("https://quotes.toscrape.com/scroll")
```

Po wykonaniu `driver.get(...)` otwiera się okno przeglądarki i ładuje strona. JavaScript wykonuje się automatycznie — po chwili na stronie pojawiają się cytaty (pierwsza strona, załadowana przez JS przy starcie).

Elementy na stronie wyszukujemy za pomocą metody `find_elements`, podając strategię wyszukiwania (CSS, XPath, id, name) i selektor:

```python
from selenium.webdriver.common.by import By

quotes = driver.find_elements(By.CSS_SELECTOR, "div.quote span.text")
print(len(quotes))  # 10 (pierwsza strona)
print(quotes[0].text)
```

`find_elements` zwraca listę obiektów `WebElement`. Właściwość `.text` daje tekst widoczny na stronie — już po renderowaniu przez JavaScript.

### `WebDriverWait` — czekanie na elementy

JavaScript potrzebuje czasu, żeby pobrać dane i wstawić je do strony. Jeśli spróbujemy wyciągnąć elementy zbyt wcześnie, strona może być jeszcze pusta. Naiwne rozwiązanie to `time.sleep(3)` — ale jest kruche: na wolnym łączu 3 sekundy mogą nie wystarczyć, na szybkim — marnujemy czas.

Selenium oferuje mechanizm **jawnego czekania** (`WebDriverWait`), który odpytuje stronę co chwilę i kontynuuje, gdy warunek zostanie spełniony:

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Czekaj do 10 sekund, aż na stronie pojawi się element div.quote
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.quote"))
)
```

`WebDriverWait(driver, 10)` oznacza: sprawdzaj warunek co pół sekundy, przez maksymalnie 10 sekund. Jeśli element pojawi się po 1 sekundzie — kontynuujemy od razu. Jeśli nie pojawi się w ciągu 10 sekund — rzucony zostanie wyjątek `TimeoutException`.

`EC.presence_of_element_located(...)` to jeden z wielu gotowych warunków z modułu `expected_conditions`. Inne przydatne warunki:

* `EC.visibility_of_element_located(...)` — element jest obecny *i* widoczny,
* `EC.element_to_be_clickable(...)` — element można kliknąć.

**Reguła: zawsze używaj `WebDriverWait` zamiast `time.sleep`.** `WebDriverWait` jest szybszy (nie czeka niepotrzebnie), odporniejszy (dostosowuje się do czasu ładowania) i czytelniejszy (jawnie mówi, na co czekamy).

### Przewijanie strony

Strona `quotes.toscrape.com/scroll` ładuje kolejne cytaty przy przewijaniu (infinite scroll). Aby załadować wszystkie, musimy programowo przewinąć stronę do końca:

```python
driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
```

`execute_script` wykonuje dowolny kod JavaScript w kontekście strony. `window.scrollTo(0, document.body.scrollHeight)` przewija na sam dół — co powoduje załadowanie kolejnej porcji cytatów.

### Kompletny przykład: wszystkie cytaty z infinite scroll

```python
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://quotes.toscrape.com/scroll")

# Czekamy na pierwszą porcję cytatów
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.quote"))
)

previous_count = 0

while True:
    # Przewiń na dół
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

    # Daj chwilę na załadowanie nowych elementów
    time.sleep(1)

    # Sprawdź, ile cytatów jest teraz na stronie
    current_count = len(driver.find_elements(By.CSS_SELECTOR, "div.quote"))

    if current_count == previous_count:
        break  # Nic nowego nie załadowano — koniec danych
    previous_count = current_count

# Ekstrakcja wszystkich cytatów
quotes = driver.find_elements(By.CSS_SELECTOR, "div.quote")
for q in quotes:
    text = q.find_element(By.CSS_SELECTOR, "span.text").text
    author = q.find_element(By.CSS_SELECTOR, "small.author").text
    print(f"{author}: {text[:60]}...")

print(f"\nŁącznie: {len(quotes)} cytatów")

driver.quit()
```

Uwagi do tego kodu:

* `time.sleep(1)` w pętli przewijania to wyjątek od reguły „nie używaj sleep" — tu czekamy nie na konkretny element, lecz na efekt uboczny przewinięcia. Alternatywą byłby `WebDriverWait` z własnym warunkiem sprawdzającym liczbę elementów, ale `sleep(1)` jest tu prostszy i wystarczający.
* Warunek stopu: `current_count == previous_count` — jeśli po przewinięciu nie pojawiły się nowe cytaty, zakładamy, że dane się skończyły.
* `driver.quit()` zamyka przeglądarkę i zwalnia zasoby. Bez tego okno Chrome pozostanie otwarte.

### Selenium vs `requests` — kluczowe różnice

| Aspekt | `requests` | Selenium |
|--------|-----------|----------|
| Wykonuje JavaScript | nie | tak |
| Szybkość | szybki (sam HTTP) | wolny (przeglądarka) |
| Zużycie zasobów | minimalne | duże (RAM, CPU) |
| Zależności | brak (czysty Python) | przeglądarka + sterownik |
| Kiedy używać | HTML zwracany przez serwer zawiera dane | dane generowane przez JavaScript |

Selenium to narzędzie **ostateczne** — używamy go, gdy prostsze metody (`requests` + parsowanie, AJAX shortcut) nie dają dostępu do danych.

---

## Drzewo decyzyjne

Poniższy diagram podsumowuje, jak dobrać narzędzie do problemu:

```
Czy dane, których szukam, są na stronie w przeglądarce?
│
├── NIE → inny problem (auth, paywall, Cloudflare, brak danych)
│
└── TAK → Czy są w HTML zwracanym przez serwer?
    │     (sprawdź: requests.get → BeautifulSoup → szukaj danych)
    │
    ├── TAK → requests + BeautifulSoup / Scrapy
    │
    └── NIE (JS-rendered) → Czy w DevTools → Network → XHR
                             widać żądania z danymi?
        │
        ├── TAK → requests bezpośrednio do API (AJAX shortcut)
        │
        └── NIE → Selenium
```

Pierwsze pytanie to zawsze: **czy dane w ogóle są na stronie?** Drugie: **czy da się je dostać bez przeglądarki?** Selenium pojawia się dopiero wtedy, gdy prostsze ścieżki zawiodą.

---

## Podsumowanie kursu

Na tym kursie przeszliśmy od ręcznego żądania HTTP do zautomatyzowanego pozyskiwania danych — budując narzędzia warstwa po warstwie:

| Narzędzie | Zastosowanie | Laby |
|-----------|-------------|------|
| `requests` | proste HTTP, API, JSON | 1–2 |
| Flask (serwer) | kontrolowane środowisko do nauki | 3–4 |
| BeautifulSoup / lxml | parsowanie HTML, selektory CSS, XPath | 5–6 |
| `requests.Session` | cookies, logowanie, formularze | 7–8 |
| `httpx.AsyncClient` | wiele żądań równolegle | 9–10 |
| Scrapy | duże projekty, crawling, pipeline | 11–12 |
| Selenium | strony JS-rendered, interakcja z przeglądarką | 13 |

Każde narzędzie rozwiązuje problem, którego poprzednie nie mogło obsłużyć. Narzędzie dobieramy do problemu, nie odwrotnie.

**Co dalej:**

* **Lab 13**: Dwie ścieżki do tych samych danych — AJAX shortcut (`requests` bezpośrednio do API `quotes.toscrape.com`) vs Selenium (infinite scroll, przewijanie, ekstrakcja z DOM). Plus opcjonalny challenge: Selenium na formularzu wyszukiwania.
