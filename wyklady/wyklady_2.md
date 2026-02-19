---
title: "Wykład 2: Serwer HTTP — od `http.server` do Flask"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

# Serwer HTTP: druga strona dialogu {-}

## Cele i zakres

Na Wykładzie 1 patrzyliśmy na HTTP wyłącznie od strony klienta: wysyłaliśmy żądania (`curl`, `requests`) i analizowaliśmy odpowiedzi. Teraz przechodzimy na **drugą stronę** — budujemy serwer, który te odpowiedzi generuje. Celem nie jest nauka web-developmentu, lecz **demistyfikacja serwera HTTP** i zbudowanie kontrolowanego środowiska do nauki scrapingu i crawlingu.

Zakres obejmuje:

* serwer HTTP jako program w Pythonie — od `http.server` do Flask,
* routing: jak serwer dopasowuje żądanie do funkcji obsługującej,
* generowanie odpowiedzi: HTML, JSON, kody statusu, nagłówki,
* serwer jako „model świata" — kontrolowane strony z linkami,
* intuicja grafowa: strony jako wierzchołki, linki jako krawędzie — przygotowanie do crawlingu.

---

## Serwer jako program

Na Wykładzie 1 serwer opisaliśmy jako „czarną skrzynkę", która odbiera żądanie i zwraca odpowiedź. Teraz otworzymy tę skrzynkę i zobaczymy, że **serwer HTTP to zwykły program** — w naszym przypadku skrypt w Pythonie — który:

1. nasłuchuje na porcie (np. `8000`),
2. odbiera żądanie HTTP (metoda, ścieżka, nagłówki, body),
3. wykonuje logikę (routing, przetwarzanie danych),
4. odsyła odpowiedź HTTP (status, nagłówki, body).

To jest dokładnie to, co widzieliśmy w `curl -v` — tyle że teraz **piszemy kod po stronie `<`** (odpowiedzi), a nie `>` (żądania).

---

## Demistyfikacja: `http.server` z biblioteki standardowej

Python ma wbudowany moduł `http.server`, który pozwala napisać serwer HTTP bez żadnych zewnętrznych zależności. Nie będziemy go używać w labach (jest zbyt niskopoziomowy), ale warto zobaczyć go raz, żeby zrozumieć, **co dokładnie robi serwer**.

### Minimalny serwer

```python
from http.server import HTTPServer, BaseHTTPRequestHandler

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Witaj! To jest odpowiedz serwera.\n")

server = HTTPServer(("localhost", 8000), MyHandler)
print("Serwer działa na http://localhost:8000")
server.serve_forever()
```

### Co robi ten kod — linia po linii

* `HTTPServer(("localhost", 8000), MyHandler)` — tworzy serwer nasłuchujący na porcie 8000.
* `MyHandler` — klasa, która definiuje, jak obsłużyć żądania. Dziedziczy po `BaseHTTPRequestHandler`.
* `do_GET(self)` — metoda wywoływana, gdy klient wyśle `GET`. (Analogicznie: `do_POST` dla `POST`.)
* `self.send_response(200)` — ustawia kod statusu. To jest to `HTTP/1.1 200 OK`, które widzieliśmy w `curl -i`.
* `self.send_header("Content-Type", ...)` — dodaje nagłówek odpowiedzi.
* `self.end_headers()` — kończy sekcję nagłówków (pusta linia przed body).
* `self.wfile.write(b"...")` — wysyła ciało odpowiedzi (bajty).

### Test klientem

Po uruchomieniu serwera, w **drugim terminalu**:

```bash
curl -i http://localhost:8000
```

Zobaczysz:

```
HTTP/1.0 200 OK
Content-Type: text/plain; charset=utf-8
...

Witaj! To jest odpowiedz serwera.
```

Albo w Pythonie:

```python
import requests
r = requests.get("http://localhost:8000")
print(r.status_code, r.text)
```

### Dostęp do informacji o żądaniu

Wewnątrz `do_GET` mamy dostęp do tego, co przysłał klient:

```python
def do_GET(self):
    print("Ścieżka:", self.path)           # np. "/hello?name=Jan"
    print("Metoda:", self.command)           # "GET"
    print("Nagłówki:", dict(self.headers))   # słownik nagłówków żądania
    # ...
```

### Serwer zwracający HTML

```python
def do_GET(self):
    html = "<html><body><h1>Strona główna</h1><p>To jest HTML.</p></body></html>"
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.end_headers()
    self.wfile.write(html.encode("utf-8"))
```

### Serwer zwracający JSON

```python
import json

def do_GET(self):
    data = {"status": "ok", "items": [1, 2, 3]}
    body = json.dumps(data).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(body)
```

### Dlaczego nie `http.server` na co dzień

Moduł `http.server` wymaga ręcznego:

* parsowania ścieżki i query string,
* rozróżniania tras (routing),
* ustawiania każdego nagłówka,
* kodowania body do bajtów.

To jest cenne dydaktycznie (widać każdy krok), ale **w praktyce produkuje dużo powtarzalnego kodu** (boilerplate), który nie uczy HTTP — tylko frustruje. Dlatego od tej pory korzystamy z Flaska.

---

## Flask — serwer HTTP jako model pojęć HTTP

Flask to mikroframework webowy dla Pythona. W tym kursie używamy go **nie** do budowania aplikacji webowych, lecz jako **wygodnego modelu serwera HTTP**, który mapuje się niemal 1:1 na pojęcia z Wykładu 1.

| Pojęcie HTTP (Wykład 1) | Odpowiednik w Flask |
|---|---|
| Routing (metoda + ścieżka → handler) | `@app.route("/path", methods=["GET"])` |
| Query string (`?key=value`) | `request.args["key"]` |
| Body żądania (formularz) | `request.form["field"]` |
| Body żądania (JSON) | `request.get_json()` |
| Kod statusu | `return ..., 200` albo `return ..., 404` |
| Nagłówek `Content-Type: text/html` | `return "<html>..."` (domyślnie) |
| Nagłówek `Content-Type: application/json` | `return jsonify({...})` |
| Nagłówki niestandardowe | `make_response()` + `response.headers[...] = ...` |

### Instalacja

```bash
pip install flask
```

Flask jest open-source (licencja BSD), nie wymaga konta ani rejestracji.

### Minimalny serwer Flask

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Witaj! To jest odpowiedź serwera."

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

Po uruchomieniu: `http://localhost:5000/`.

Porównaj z wersją `http.server` — **ten sam efekt**, ale bez ręcznego `send_response`, `send_header`, `end_headers`, `wfile.write`.

### Routing — dopasowanie żądania do funkcji

Serwer musi umieć rozróżnić, czego dotyczy żądanie. W Flask robi to **dekorator `@app.route`**:

```python
@app.route("/")
def index():
    return "Strona główna"

@app.route("/about")
def about():
    return "O nas"

@app.route("/items")
def items_list():
    return "Lista przedmiotów"
```

Każda funkcja obsługuje **jedną trasę** (ścieżkę). Gdy klient wysyła `GET /about`, Flask wywołuje `about()`.

### Parametry w ścieżce (zmienne trasowe)

```python
@app.route("/items/<int:item_id>")
def item_detail(item_id):
    return f"Szczegóły przedmiotu nr {item_id}"
```

* `<int:item_id>` — Flask wyciąga fragment ścieżki, konwertuje na `int` i przekazuje jako argument.
* `GET /items/42` → `item_detail(42)` → `"Szczegóły przedmiotu nr 42"`.

To jest wzorzec **kolekcja / element** z Wykładu 1 (`/items` vs `/items/42`), zaimplementowany po stronie serwera.

### Query string — `request.args`

```python
from flask import Flask, request

@app.route("/search")
def search():
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    return f"Szukam: {q}, strona: {page}"
```

* `request.args` to słownik-podobny obiekt z parametrami query string.
* `GET /search?q=python&page=2` → `search()` → `"Szukam: python, strona: 2"`.

To jest dokładnie to, co po stronie klienta podawaliśmy jako `params={"q": "python", "page": 2}` w `requests.get()`.

### Metody HTTP

Domyślnie `@app.route` obsługuje tylko `GET`. Żeby obsłużyć inne metody:

```python
@app.route("/items", methods=["GET", "POST"])
def items():
    if request.method == "GET":
        return "Lista przedmiotów"
    elif request.method == "POST":
        data = request.get_json()
        return f"Tworzę: {data}", 201
```

### Kody statusu

Domyślnie Flask zwraca `200`. Inny kod podajemy jako drugi element krotki:

```python
@app.route("/items/<int:item_id>")
def item_detail(item_id):
    if item_id > 100:
        return "Nie znaleziono", 404
    return f"Przedmiot {item_id}"
```

Test:

```bash
curl -i http://localhost:5000/items/999
# HTTP/1.1 404 NOT FOUND
# ...
# Nie znaleziono
```

Student widzi teraz **obie strony**: klient wysyła żądanie, serwer decyduje o kodzie.

### Zwracanie JSON — `jsonify()`

```python
from flask import Flask, jsonify

@app.route("/api/items")
def api_items():
    items = [
        {"id": 1, "name": "Jabłko"},
        {"id": 2, "name": "Gruszka"},
    ]
    return jsonify(items)
```

`jsonify()` robi dwie rzeczy:

1. serializuje dane do JSON,
2. ustawia `Content-Type: application/json`.

To jest odpowiednik tego, co w `http.server` wymagało ręcznego `json.dumps()` + `send_header("Content-Type", "application/json")`.

### Zwracanie HTML

```python
@app.route("/page")
def page():
    return """
    <html>
    <body>
        <h1>Tytuł strony</h1>
        <p>To jest akapit.</p>
        <a href="/other">Link do innej strony</a>
    </body>
    </html>
    """
```

Flask domyślnie ustawia `Content-Type: text/html`. Przeglądarka renderuje HTML; `curl` i `requests` widzą surowy tekst.

### Generowanie HTML dynamicznie

Serwer nie musi zwracać stałego tekstu — może **generować HTML** na podstawie danych:

```python
@app.route("/numbers")
def numbers():
    html = "<html><body><h1>Liczby</h1><ul>"
    for i in range(1, 11):
        html += f'<li><a href="/numbers/{i}">Liczba {i}</a></li>'
    html += "</ul></body></html>"
    return html

@app.route("/numbers/<int:n>")
def number_detail(n):
    return f"""
    <html><body>
        <h1>Liczba {n}</h1>
        <p>Kwadrat: {n**2}</p>
        <a href="/numbers">Powrót do listy</a>
    </body></html>
    """
```

Ten serwer tworzy **sieć stron połączonych linkami**: strona `/numbers` linkuje do `/numbers/1`, `/numbers/2`, ..., a każda z nich linkuje z powrotem. To jest dokładnie struktura, po której będziemy się poruszać crawlerem.

---

## Serwer jako kontrolowane środowisko

W Labach 1–2 korzystaliśmy z publicznego API (dane.gov.pl). Było to dobre do nauki klientów HTTP, ale miało ograniczenia:

* brak kontroli nad strukturą danych,
* brak kontroli nad kodami błędów i opóźnieniami,
* ryzyko obciążenia cudzego serwera,
* zależność od dostępności zewnętrznej usługi.

Od teraz tworzymy **własne serwery lokalne** — małe programy Flask, które:

* serwują strony HTML z kontrolowaną strukturą (tabele, linki, formularze),
* zwracają JSON z przewidywalnymi danymi,
* mogą symulować błędy (`404`, `500`), opóźnienia (`time.sleep`), paginację,
* działają offline, na komputerze studenta.

To jest **laboratorium**, w którym uczymy się parsowania HTML, crawlingu, obsługi sesji — bez ryzyka i z pełną powtarzalnością.

### Przykład: serwer z paginacją

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

# Symulowane dane
ALL_ITEMS = [{"id": i, "name": f"Element {i}"} for i in range(1, 51)]

@app.route("/api/items")
def items():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    
    start = (page - 1) * per_page
    end = start + per_page
    page_items = ALL_ITEMS[start:end]
    
    response = {
        "data": page_items,
        "meta": {"total": len(ALL_ITEMS), "page": page, "per_page": per_page},
    }
    
    if end < len(ALL_ITEMS):
        response["links"] = {"next": f"/api/items?page={page+1}&per_page={per_page}"}
    
    return jsonify(response)
```

Ten serwer zachowuje się **dokładnie jak API dane.gov.pl** — ma paginację, `meta`, `links.next` — ale działa lokalnie i ma 50 elementów zamiast tysięcy.

### Przykład: serwer symulujący błędy

```python
@app.route("/api/flaky")
def flaky():
    import random
    if random.random() < 0.3:
        return jsonify({"error": "Server overloaded"}), 503
    return jsonify({"status": "ok"})
```

Przydatny do testowania logiki retry z Labu 2 — bez czekania, aż prawdziwy serwer się „zepsuje".

---

## Strony z linkami — przygotowanie do crawlingu

Kluczową aplikacją serwera lokalnego w tym kursie jest tworzenie **sieci stron połączonych hiperłączami**. To jest materiał, na którym będziemy ćwiczyć crawling (Lab 4).

### Przykład: ciąg Collatza

Ciąg Collatza (problem 3n+1) generuje dla danej liczby naturalnej sekwencję:

* jeśli n jest parzyste → n/2,
* jeśli n jest nieparzyste → 3n+1,
* koniec, gdy n = 1.

Każdą liczbę możemy przedstawić jako stronę HTML, a przejście do następnej — jako link:

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

Z perspektywy klienta: `GET /collatz/6` zwraca HTML z linkiem do `/collatz/3`, ten do `/collatz/10`, itd. **Program, który automatycznie podąża za tymi linkami, to crawler.**

---

## Intuicja grafowa: strony i linki

Zanim napiszemy crawler (Lab 4), potrzebujemy jednego pojęcia ze świata grafów. Nie będziemy formalizować teorii — wystarczy intuicja.

### Strony jako wierzchołki, linki jako krawędzie

Wyobraź sobie serwer, który ma 5 stron. Każda strona zawiera linki do niektórych innych:

```
Strona A  →  Strona B, Strona C
Strona B  →  Strona A, Strona D
Strona C  →  Strona D
Strona D  →  Strona E
Strona E  →  Strona A
```

To jest **graf skierowany**:

* **wierzchołki** = strony (A, B, C, D, E),
* **krawędzie** = linki (A→B oznacza: „strona A zawiera link do strony B").

### Crawling = przeszukiwanie grafu

Crawler to program, który:

1. zaczyna od strony startowej (np. A),
2. pobiera jej HTML,
3. wyciąga z niej linki (np. B i C),
4. dodaje je do kolejki „do odwiedzenia",
5. powtarza — pobiera następną stronę z kolejki, wyciąga linki, itd.

Kluczowy problem: **unikanie cykli**. W powyższym grafie A→B→A→B→... to pętla nieskończona. Rozwiązanie: pamiętaj zbiór **odwiedzonych** URL-ów i nie odwiedzaj ich ponownie.

```
visited = {A}
queue = [B, C]         # linki z A

visit B → visited = {A, B}, queue = [C, D]     # A już odwiedzone, pomijamy
visit C → visited = {A, B, C}, queue = [D]     # D już w kolejce? to zależy od implementacji
visit D → visited = {A, B, C, D}, queue = [E]
visit E → visited = {A, B, C, D, E}, queue = [] # A odwiedzone, pomijamy

Koniec — wszystkie strony odwiedzone.
```

To jest algorytm **BFS** (przeszukiwanie wszerz), ale nie musisz znać tej nazwy — wystarczy wzorzec: **kolejka + zbiór odwiedzonych**.

### Od grafów do crawlera

W Labie 4 napiszemy crawler, który:

1. pobiera stronę HTML z lokalnego serwera (`requests.get`),
2. wyciąga z niej linki (na razie regex lub `str.split` — bez BeautifulSoup, bo to Wykład 3),
3. filtruje linki (tylko te prowadzące do naszego serwera),
4. dodaje nieodwiedzone do kolejki,
5. powtarza, aż kolejka jest pusta lub osiągnie limit.

To będzie nasz pierwszy „robot" automatycznie przechodzący po stronach.

---

## Flask: generowanie odpowiedzi — szczegóły

Poniżej zestawienie technik, które będą przydatne w labach.

### Obiekt `response` i nagłówki niestandardowe

```python
from flask import Flask, make_response

@app.route("/custom")
def custom():
    resp = make_response("Treść odpowiedzi")
    resp.headers["X-Custom-Header"] = "wartość"
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.status_code = 200
    return resp
```

`make_response()` daje pełną kontrolę nad odpowiedzią — analogicznie do ręcznych `send_header` w `http.server`, ale wygodniej.

### Przekierowania

```python
from flask import redirect

@app.route("/old-page")
def old_page():
    return redirect("/new-page", code=301)

@app.route("/new-page")
def new_page():
    return "To jest nowa strona."
```

Test:

```bash
curl -i http://localhost:5000/old-page
# HTTP/1.1 301 MOVED PERMANENTLY
# Location: /new-page

curl -L http://localhost:5000/old-page
# To jest nowa strona.
```

Student widzi przekierowanie (`301` + `Location:`) z obu stron — i wie, dlaczego `curl -L` lub `requests` (które domyślnie podąża za przekierowaniami) trafia na właściwą stronę.

### Zwracanie plików

```python
from flask import send_file

@app.route("/download/data.csv")
def download_csv():
    return send_file("data/sample.csv", as_attachment=True)
```

Przydatne, gdy serwer ma serwować pliki danych — analogicznie do `Download URL` z API dane.gov.pl (Lab 2).

### Obsługa błędów

```python
from flask import abort

@app.route("/items/<int:item_id>")
def item(item_id):
    if item_id not in ITEMS_DB:
        abort(404)
    return jsonify(ITEMS_DB[item_id])
```

`abort(404)` przerywa obsługę żądania i zwraca odpowiedź z kodem 404. Można też zdefiniować własne strony błędów:

```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Nie znaleziono"}), 404
```

---

## Serwer i klient — dwie strony dialogu

Po tym wykładzie student widzi **pełny obraz** komunikacji HTTP:

```
     KLIENT                                SERWER
     ──────                                ──────
     requests.get(                         @app.route("/items",
       "/items",                              methods=["GET"])
       params={"page": 2}                  def items():
     )                                        page = request.args.get("page")
                          ─── GET /items?page=2 ───►
                          ◄── 200 OK, JSON ────
     
     r.status_code  ←  200                 return jsonify(data), 200
     r.json()       ←  {"data": [...]}     jsonify(data)
     r.headers      ←  Content-Type: ...   (automatycznie)
```

To jest ta sama wymiana komunikatów, którą widzieliśmy w `curl -v` na Wykładzie 1 — tyle że teraz rozumiemy **obie strony**.

---

## Uruchamianie serwera Flask — praktyczne uwagi

### Tryb `debug`

```python
app.run(debug=True, port=5000)
```

`debug=True` włącza:

* **auto-reload** — serwer restartuje się po zmianie kodu (nie trzeba ręcznie go zatrzymywać i uruchamiać),
* **debugger** — przy błędzie w kodzie serwera, w przeglądarce pojawia się szczegółowy traceback.

W labach zawsze używamy `debug=True`. W produkcji — nigdy.

### Port

Domyślnie Flask używa portu `5000`. Jeśli jest zajęty, podaj inny:

```python
app.run(debug=True, port=8080)
```

### Dwa terminale

Typowy workflow w labie:

* **Terminal 1**: uruchomiony serwer (`python server.py`),
* **Terminal 2**: klient — `curl`, skrypt Pythona z `requests`, albo Jupyter Notebook.

Serwer musi **działać w tle**, gdy wysyłasz do niego żądania. To jest naturalna konsekwencja modelu klient–serwer.

---

## Podsumowanie

Na tym wykładzie:

* zobaczyliśmy serwer HTTP „od środka" — od `http.server` (nisko, jawnie) do Flask (wygodnie, z mapowaniem na pojęcia HTTP),
* poznaliśmy Flask jako narzędzie do budowania kontrolowanych środowisk dydaktycznych,
* nauczyliśmy się generować HTML z linkami — podstawa do crawlingu,
* zbudowaliśmy intuicję grafową (strony = wierzchołki, linki = krawędzie, crawler = przeszukiwanie grafu).

**Co dalej:**

* **Lab 3**: budujemy serwer Flask — strony z linkami (ciąg Collatza), mini-API, testowanie klientami (`curl`, `requests`, przeglądarka).
* **Lab 4**: piszemy crawlera w `requests`, który automatycznie przechodzi po stronach serwera z Labu 3, zbiera dane i zapisuje je do pliku.