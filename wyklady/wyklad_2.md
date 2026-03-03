---
title: "Wykład 2: Serwer HTTP - framework Flask"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

## Cele i zakres

Na Wykładzie 1 patrzyliśmy na HTTP wyłącznie od strony klienta: wysyłaliśmy żądania (`curl`, `requests`) i analizowaliśmy odpowiedzi. Teraz przechodzimy na **drugą stronę** — budujemy serwer, który te odpowiedzi generuje.

Celem nie jest nauka web-developmentu, lecz:

* **zrozumienie serwera HTTP** — co robi program, który odpowiada na żądania,
* **opanowanie Flaska** jako narzędzia do budowania kontrolowanych środowisk.

Zakres obejmuje:

* serwer HTTP jako program w Pythonie,
* Flask: routing, parametry, metody HTTP, kody statusu, generowanie HTML i JSON,
* dynamiczne generowanie stron — serwer jako „model świata",
* serwer jako kontrolowane środowisko do nauki crawlingu.

---

## Serwer jako program

Na Wykładzie 1 serwer opisaliśmy jako „czarną skrzynkę", która odbiera żądanie i zwraca odpowiedź. Teraz otworzymy tę skrzynkę i zobaczymy, że **serwer HTTP to zwykły program** — w naszym przypadku skrypt w Pythonie — który:

1. nasłuchuje na porcie (np. `5000`),
2. odbiera żądanie HTTP (metoda, ścieżka, nagłówki, body),
3. wykonuje logikę (routing, przetwarzanie danych),
4. odsyła odpowiedź HTTP (status, nagłówki, body).

To jest dokładnie to, co widzieliśmy w `curl -v` — tyle że teraz **piszemy kod po stronie `<`** (odpowiedzi), a nie `>` (żądania).

### Co robi serwer „pod maską"

Gdy piszemy we Flasku `return "Witaj!", 200` — framework wykonuje za nas operacje, które na poziomie protokołu wyglądają tak:

```
1. Przyjmij połączenie TCP na porcie 5000
2. Odczytaj żądanie:   GET / HTTP/1.1\r\nHost: localhost:5000\r\n...
3. Dopasuj ścieżkę "/" do funkcji obsługującej (routing)
4. Wywołaj funkcję → zwróć tekst "Witaj!" i kod 200
5. Zbuduj odpowiedź:   HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\nWitaj!
6. Wyślij odpowiedź do klienta
7. Zamknij połączenie (lub utrzymaj, jeśli keep-alive)
```

Kroki 1–2 i 5–7 to niskopoziomowa obsługa protokołu — Flask robi je automatycznie. My piszemy **tylko krok 3–4**: trasę i logikę.

Python ma wbudowany moduł `http.server`, który pozwala napisać serwer bez żadnych zależności zewnętrznych. Wymaga on ręcznego wykonywania każdego z tych kroków — ustawiania kodu statusu, nagłówków, kodowania body do bajtów. Jest cenny poznawczo (widać każdy bajt), ale produkuje dużo powtarzalnego kodu. Dlatego od razu korzystamy z Flaska.

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

Flask jest frameworkiem open-source (licencja BSD).

### Minimalny serwer Flask

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Witaj! To jest odpowiedź serwera."
```

Zapisz ten kod jako `app.py` i uruchom w terminalu poleceniem `flask run --debug -p 5000` (szczegóły — w sekcji „Uruchamianie serwera" na końcu wykładu). Po uruchomieniu otwórz w przeglądarce `http://localhost:5000/`.

Test klientem:

```bash
curl -i http://localhost:5000/
```

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 38
...

Witaj! To jest odpowiedź serwera.
```


---

## Routing — dopasowanie żądania do funkcji

Serwer musi umieć rozróżnić, czego dotyczy żądanie. Przeglądarka wysyła `GET /about` — serwer musi wiedzieć, jaką funkcję wywołać. W Flask robi to **dekorator `@app.route`**:

```python
@app.route("/")
def index():
    return "Strona główna"

@app.route("/about")
def about():
    return "O nas"

@app.route("/contact")
def contact():
    return "Kontakt: email@example.com"
```

Każda funkcja obsługuje **jedną trasę** (ścieżkę). Gdy klient wysyła `GET /about`, Flask wywołuje `about()`. Gdy ścieżka nie pasuje do żadnej trasy — Flask zwraca `404`.

### Parametry w ścieżce (zmienne trasowe)

Na Wykładzie 1 widzieliśmy wzorzec kolekcja / element w URL-ach API: `/datasets` (lista) vs `/datasets/830` (konkretny zbiór). Serwer musi umieć wyciągnąć `830` ze ścieżki i przekazać do logiki. Flask robi to tak:

```python
@app.route("/items/<int:item_id>")
def item_detail(item_id):
    return f"Szczegóły przedmiotu nr {item_id}"
```

* `<int:item_id>` — Flask wyciąga fragment ścieżki, konwertuje na `int` i przekazuje jako argument funkcji.
* `GET /items/42` → `item_detail(42)` → `"Szczegóły przedmiotu nr 42"`.
* `GET /items/abc` → Flask zwraca `404` (bo `abc` nie jest `int`).

Dostępne konwertery: `int`, `float`, `string` (domyślny — dowolny tekst bez `/`), `path` (tekst z `/`).

```python
@app.route("/users/<username>")
def user_profile(username):
    return f"Profil użytkownika: {username}"
```

`GET /users/anna` → `user_profile("anna")`.

### Query string — `request.args`

Na Wykładzie 1 po stronie klienta pisaliśmy `params={"q": "python", "page": 2}` w `requests.get()`. Po stronie serwera te parametry trafiają do `request.args`:

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/search")
def search():
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    return f"Szukam: '{q}', strona: {page}"
```

* `request.args` to słownik-podobny obiekt z parametrami query string.
* `GET /search?q=python&page=2` → `"Szukam: 'python', strona: 2"`.
* `request.args.get("page", 1, type=int)` — jeśli brak parametru, zwraca `1`; jeśli jest, konwertuje na `int`.

Uwaga: `request` w Flasku to **obiekt globalny** (a dokładniej: kontekstowy), dostępny wewnątrz funkcji obsługującej żądanie. Nie jest to parametr funkcji — Flask zarządza nim automatycznie.

---

## Metody HTTP

Domyślnie `@app.route` obsługuje tylko `GET`. Żeby obsłużyć inne metody, podajemy je jawnie:

```python
@app.route("/items", methods=["GET", "POST"])
def items():
    if request.method == "GET":
        return "Lista przedmiotów"
    elif request.method == "POST":
        data = request.get_json()
        return f"Tworzę: {data}", 201
```

* `request.method` — string z nazwą metody (`"GET"`, `"POST"`, ...).
* `request.get_json()` — parsuje body żądania z JSON do dict/list.

Test POST-em:

```bash
curl -X POST http://localhost:5000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Jabłko"}'
```

Na razie `POST` pokazujemy jako mechanizm — pełne zastosowanie (formularze, logowanie) pojawi się na Wykładzie 4.

---

## Kody statusu

Domyślnie Flask zwraca `200 OK`. Inny kod podajemy jako drugi element krotki w `return`:

```python
@app.route("/items/<int:item_id>")
def item_detail(item_id):
    if item_id > 100:
        return "Nie znaleziono", 404
    return f"Przedmiot {item_id}"
```

Test:

```bash
curl -i http://localhost:5000/items/42
# HTTP/1.1 200 OK
# Przedmiot 42

curl -i http://localhost:5000/items/999
# HTTP/1.1 404 NOT FOUND
# Nie znaleziono
```

---

## Zwracanie JSON — `jsonify()`

Serwer, który generuje JSON:

```python
from flask import Flask, jsonify

app = Flask(__name__)

ITEMS = [
    {"id": 1, "name": "Jabłko", "category": "Owoce"},
    {"id": 2, "name": "Marchewka", "category": "Warzywa"},
    {"id": 3, "name": "Chleb", "category": "Pieczywo"},
]

@app.route("/api/items")
def api_items():
    return jsonify(ITEMS)
```

`jsonify()` robi dwie rzeczy:

1. serializuje dane do JSON (`json.dumps` pod spodem),
2. ustawia `Content-Type: application/json`.

Test:

```bash
curl -s http://localhost:5000/api/items | python3 -m json.tool
```

Albo w Pythonie:

```python
import requests

r = requests.get("http://localhost:5000/api/items")
r.raise_for_status()
items = r.json()
for item in items:
    print(f"  [{item['id']}] {item['name']}")
```

Klient nie odróżnia „lokalnego Flaska" od „API dane.gov.pl" — to ten sam protokół, ten sam format, ten sam kod klienta.

### Kolekcja z danymi w słowniku

API często opakowuje listę wyników w słownik z metadanymi — jak `dane.gov.pl`:

```python
@app.route("/api/items")
def api_items():
    return jsonify({
        "data": ITEMS,
        "meta": {"count": len(ITEMS)},
    })
```

---

## Zwracanie HTML

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

Różnica między HTML a JSON z perspektywy serwera sprowadza się do jednego: **co zwracasz i jaki `Content-Type` ustawiasz**. Flask wybiera domyślnie `text/html`; `jsonify()` przełącza na `application/json`.

---

## Generowanie HTML dynamicznie

Serwer nie musi zwracać stałego tekstu — może **generować HTML** na podstawie danych i logiki. To jest kluczowa umiejętność: serwery lokalne, które będziemy budować w kursie, będą generować strony z tabelami, listami i linkami — jako materiał do parsowania i scrapingu.

### Lista z linkami

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
        <p>Sześcian: {n**3}</p>
        <a href="/numbers">Powrót do listy</a>
    </body></html>
    """
```

Ten serwer tworzy **sieć stron połączonych linkami**: strona `/numbers` linkuje do `/numbers/1`, `/numbers/2`, ..., a każda z nich linkuje z powrotem do listy.

### Tabela z danymi

```python
@app.route("/products")
def products():
    items = [
        {"name": "Jabłko", "price": 3.50, "unit": "kg"},
        {"name": "Chleb", "price": 5.00, "unit": "szt"},
        {"name": "Mleko", "price": 4.20, "unit": "l"},
    ]
    
    rows = ""
    for item in items:
        rows += f"""
        <tr>
            <td>{item['name']}</td>
            <td>{item['price']:.2f} zł</td>
            <td>{item['unit']}</td>
        </tr>"""
    
    return f"""
    <html><body>
        <h1>Produkty</h1>
        <table border="1">
            <tr><th>Nazwa</th><th>Cena</th><th>Jednostka</th></tr>
            {rows}
        </table>
    </body></html>
    """
```


### Dane z logiki — ciąg Collatza

Serwer może generować strony na podstawie obliczeń. Ciąg Collatza (problem 3n+1) generuje dla danej liczby naturalnej sekwencję: jeśli n jest parzyste → n/2, jeśli nieparzyste → 3n+1, aż do 1. Każdą liczbę prezentujemy jako stronę HTML, a przejście do następnej — jako link:

```python
@app.route("/collatz/<int:n>")
def collatz(n):
    if n < 1:
        return "Liczba musi być dodatnia", 400
    
    if n == 1:
        return """
        <html><body>
            <h1>Collatz: 1</h1>
            <p>Koniec ciągu!</p>
            <a href="/collatz/7">Rozpocznij od 7</a>
        </body></html>
        """
    
    next_n = n // 2 if n % 2 == 0 else 3 * n + 1
    
    return f"""
    <html><body>
        <h1>Collatz: {n}</h1>
        <p>Następna liczba: {next_n}</p>
        <a href="/collatz/{next_n}">Przejdź do {next_n}</a>
    </body></html>
    """
```

Z perspektywy klienta: `GET /collatz/6` zwraca HTML z linkiem do `/collatz/3`, ten do `/collatz/10`, itd. To jest sieć stron, po której można nawigować ręcznie (w przeglądarce) lub automatycznie (programem). Serwery o takiej strukturze — strony powiązane linkami — będą bazą do nauki crawlingu i scrapingu w dalszej części kursu.

---

## Serwer jako kontrolowane środowisko

Wcześniej korzystaliśmy z publicznego API (dane.gov.pl). Było to dobre do nauki klientów HTTP, ale miało ograniczenia:

* brak kontroli nad strukturą danych,
* brak kontroli nad kodami błędów i opóźnieniami,
* ryzyko obciążenia cudzego serwera,
* zależność od dostępności zewnętrznej usługi.

Teraz możemy tworzyć **własne serwery lokalne** — programy Flask, które:

* serwują strony HTML z kontrolowaną strukturą (tabele, listy, linki),
* zwracają JSON z przewidywalnymi danymi,
* mogą symulować błędy (`404`, `500`), opóźnienia (`time.sleep`), paginację,
* działają offline.

### Przykład: serwer z paginacją

Na Labie 2 pisaliśmy klienta, który pobierał kolejne strony wyników z API dane.gov.pl. Teraz zobaczymy, jak taka paginacja wygląda **po stronie serwera**:

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

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
        response["links"] = {
            "next": f"/api/items?page={page + 1}&per_page={per_page}"
        }
    
    return jsonify(response)
```

Ten serwer zachowuje się **dokładnie jak API dane.gov.pl** — ma paginację, `meta`, `links.next` — ale działa lokalnie i ma 50 elementów zamiast tysięcy.

### Przykład: serwer symulujący błędy

```python
import random
import time

@app.route("/api/flaky")
def flaky():
    if random.random() < 0.3:
        return jsonify({"error": "Server overloaded"}), 503
    return jsonify({"status": "ok"})

@app.route("/api/slow")
def slow():
    time.sleep(3)
    return jsonify({"status": "done"})
```

Przydatne do testowania logiki retry i timeoutów — bez czekania, aż prawdziwy serwer się „zepsuje".

---

## Serwer i klient — dwie strony dialogu

Po tym wykładzie widzimy **pełny obraz** komunikacji HTTP:

```
     KLIENT                                SERWER
     ──────                                ──────
     requests.get(                         @app.route("/api/items",
       "/api/items",                          methods=["GET"])
       params={"page": 2}                  def items():
     )                                        page = request.args.get("page")
                          ─── GET /api/items?page=2 ───►
                          ◄── 200 OK, JSON ────────────
     
     r.status_code  ←  200                 return jsonify(data), 200
     r.json()       ←  {"data": [...]}     jsonify(data)
     r.headers      ←  Content-Type: ...   (automatycznie)
```

To jest ta sama wymiana komunikatów, którą widzieliśmy w `curl -v` na Wykładzie 1 — tyle że teraz rozumiemy **obie strony**.

---

## Narzędzia na przyszłość

Poniżej trzy mechanizmy Flaska, które **na tym wykładzie tylko sygnalizujemy**. Użyjemy ich w pełni na Wykładzie 4 (cookies, sesje, formularze) — tutaj wystarczy wiedzieć, że istnieją.

### `make_response` — pełna kontrola nad odpowiedzią

```python
from flask import make_response

@app.route("/custom")
def custom():
    resp = make_response("Treść odpowiedzi")
    resp.headers["X-Custom-Header"] = "wartość"
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp
```

Przydatne, gdy standardowy `return` nie wystarcza — np. gdy chcesz ustawić cookies, nagłówki cache'owania lub niestandardowy `Content-Type`.

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

`redirect()` zwraca odpowiedź z kodem `3xx` i nagłówkiem `Location:` — dokładnie to, co omawialiśmy na Wykładzie 1. Przekierowania pojawią się przy obsłudze logowania (Wykład 4).

### `abort` — przerwanie z kodem błędu

```python
from flask import abort

@app.route("/items/<int:item_id>")
def item(item_id):
    if item_id not in ITEMS_DB:
        abort(404)
    return jsonify(ITEMS_DB[item_id])
```

`abort(404)` natychmiast przerywa obsługę żądania i zwraca odpowiedź z kodem 404. Można też zdefiniować własne strony błędów:

```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Nie znaleziono"}), 404
```

---

## Uruchamianie serwera — jak to działa w praktyce

### Przejście na VSCode

Na Labach 0–2 pracowaliśmy w Thonnym — wystarczał do pisania prostych skryptów i uruchamiania ich klawiszem F5. Od tego momentu potrzebujemy czegoś więcej: **edytora kodu** i **terminala** działających jednocześnie. Serwer Flask działa w nieskończoność (nasłuchuje na porcie i czeka na żądania), a my musimy równolegle pisać i uruchamiać klienta, który do tego serwera wysyła żądania.

**Visual Studio Code (VSCode)** daje nam to naturalnie: edytor na górze, terminal (lub kilka terminali) na dole. Wszystko w jednym oknie.

### Jak uruchomić serwer Flask

Flask udostępnia polecenie `flask run`, które uruchamia serwer. Żeby zadziałało, potrzebujemy dwóch rzeczy:

1. **Plik `app.py`** — Flask domyślnie szuka pliku o tej nazwie w bieżącym katalogu. To jest konwencja: jeśli nazwiesz plik `app.py`, nie musisz niczego konfigurować.
2. **Obiekt `app`** wewnątrz tego pliku — Flask szuka zmiennej `app` będącej instancją `Flask(...)`. To jest kolejna konwencja.

Żadnego specjalnego bloku uruchamiającego nie potrzeba. Plik `app.py` zawiera **definicję** serwera (trasy, logikę), a polecenie `flask run` zajmuje się jego **uruchomieniem**.

### Kompletny przykład krok po kroku

**Krok 1.** Utwórz katalog na projekt (np. `lab3`) i otwórz go w VSCode (`File → Open Folder...`).

**Krok 2.** Utwórz plik `app.py`:

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Serwer działa!"

@app.route("/hello/<name>")
def hello(name):
    return f"Cześć, {name}!"
```

Zwróć uwagę: plik nie ma żadnego `app.run(...)` ani bloku `if __name__`. Definicja serwera to trasy i funkcje — nic więcej.

**Krok 3.** Otwórz terminal w VSCode (`Ctrl+`` ` lub `View → Terminal`). Upewnij się, że jesteś w katalogu z plikiem `app.py`. Uruchom serwer:

```bash
flask run --debug -p 5000
```

W terminalu zobaczysz:

```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
```

Serwer działa i nasłuchuje. Terminal jest zajęty — to normalne.

**Krok 4.** Otwórz przeglądarkę i wpisz `http://localhost:5000/`. Powinieneś zobaczyć „Serwer działa!". Wpisz `http://localhost:5000/hello/Anna` — zobaczysz „Cześć, Anna!".

W terminalu VSCode zobaczysz logi — Flask wypisuje każde żądanie:

```
127.0.0.1 - - [15/Mar/2025 10:30:00] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [15/Mar/2025 10:30:05] "GET /hello/Anna HTTP/1.1" 200 -
```

To jest **perspektywa serwera** na komunikację HTTP — widzi adres klienta, metodę, ścieżkę i kod statusu, który sam zwrócił.

**Krok 5.** Żeby przetestować serwer `requests`-em lub `curl`-em, otwórz **drugi terminal** w VSCode (ikona `+` obok karty terminala, lub `Ctrl+Shift+``  `). Teraz masz dwa terminale: w jednym działa serwer, w drugim możesz uruchamiać komendy.

W drugim terminalu:

```bash
curl -i http://localhost:5000/hello/Anna
```

Albo utwórz plik `client.py` i uruchom go z drugiego terminala:

```python
import requests

r = requests.get("http://localhost:5000/hello/Anna")
print("Status:", r.status_code)
print("Treść:", r.text)
```

```bash
python client.py
```

### Flagi polecenia `flask run`

* `--debug` — włącza tryb debugowania: **auto-reload** (po zapisaniu zmian w `app.py` serwer automatycznie się restartuje) i **debugger** (przy błędzie w kodzie serwera przeglądarka pokazuje traceback zamiast ogólnego „Internal Server Error").
* `-p 5000` (lub `--port 5000`) — port, na którym serwer nasłuchuje. Domyślnie `5000`. Jeśli jest zajęty, użyj innego (np. `-p 5001`).
* `-h 0.0.0.0` (lub `--host 0.0.0.0`) — serwer dostępny z innych komputerów w sieci. Domyślnie (`127.0.0.1`) serwer nasłuchuje tylko na localhost. Na labach używamy domyślnego ustawienia.

W labach zawsze uruchamiamy z `--debug`. Polecenie, które będziemy wpisywać na początku każdego labu:

```bash
flask run --debug -p 5000
```

### Workflow w labie

```
┌──────────────────────────────────────────────────────┐
│  VSCode                                              │
│  ┌────────────────────────────────────────────────┐  │
│  │  app.py (edytor)                               │  │
│  │                                                 │  │
│  │  from flask import Flask                        │  │
│  │  app = Flask(__name__)                          │  │
│  │  ...                                            │  │
│  └────────────────────────────────────────────────┘  │
│  ┌──────────────────────┐┌─────────────────────────┐ │
│  │ Terminal 1: serwer   ││ Terminal 2: klient      │ │
│  │                      ││                          │ │
│  │ $ flask run --debug  ││ $ curl localhost:5000/   │ │
│  │ * Running on ...     ││ Serwer działa!           │ │
│  │ "GET / HTTP/1.1" 200 ││                          │ │
│  └──────────────────────┘└─────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

* **Edytor**: plik `app.py` (i inne pliki projektu). Tu piszesz kod serwera.
* **Terminal 1 (serwer)**: `flask run --debug -p 5000`. Działa cały czas. Tu widzisz logi żądań.
* **Terminal 2 (klient)**: `curl`, `python client.py`, lub przeglądarka. Tu testujesz serwer.

### Zatrzymywanie serwera

`Ctrl+C` w terminalu, w którym działa serwer. Jeśli port pozostaje „zajęty" po zamknięciu (błąd „Address already in use"), poczekaj kilka sekund lub zmień port.

### Plik o innej nazwie niż `app.py`

Jeśli nazwiesz plik inaczej (np. `server.py`), musisz powiedzieć Flaskowi, gdzie szukać aplikacji:

```bash
flask --app server run --debug -p 5000
```

Opcja `--app server` wskazuje moduł `server.py`. Na labach trzymamy się konwencji `app.py`, żeby unikać tej dodatkowej konfiguracji.

### Najczęstsze problemy

**„Address already in use"** — port jest zajęty. Zatrzymaj poprzednią instancję serwera (może działa w innym terminalu?) lub zmień port (`-p 5001`).

**„Could not import 'app'"** — Flask nie znalazł pliku `app.py` w bieżącym katalogu. Sprawdź, czy terminal jest otwarty w katalogu z plikiem (`ls` / `dir` powinno pokazać `app.py`).

**Przeglądarka pokazuje „Nie można połączyć"** — sprawdź, czy serwer jest uruchomiony (logi w terminalu) i czy adres jest poprawny (`http://localhost:5000/`, nie `https://`).

---

## Podsumowanie

Na tym wykładzie:

* zobaczyliśmy, że serwer HTTP to program, który nasłuchuje na porcie i odpowiada na żądania,
* poznaliśmy Flask jako model serwera HTTP: routing, parametry ścieżki, query string, kody statusu, `jsonify()`, generowanie HTML,
* nauczyliśmy się dynamicznie generować strony HTML z danymi, linkami i tabelami,
* zrozumieliśmy, dlaczego tworzymy własne serwery lokalne — jako kontrolowane środowisko do nauki.

**Co dalej:**

* **Lab 3**: budujemy serwer Flask od zera — routing, generowanie HTML z linkami, endpointy JSON. Testujemy go `curl`-em, `requests`-em i przeglądarką.
* **Lab 4**: budujemy bardziej złożone serwery — paginacja (jak dane.gov.pl), katalog danych z tabelami (materiał do przyszłego parsowania), symulacja błędów. Testujemy kodem klienta z Labów 1–2.