---
title: "Lab 3: Tworzenie serwera HTTP w Flask"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Uruchamianie serwera Flask i praca z dwoma terminalami (serwer + klient),
* Definiowanie tras (`@app.route`) zwracających tekst, HTML i JSON,
* Obsługa parametrów: query string (`request.args`) i zmienne trasowe (`<int:...>`),
* Obsługa żądań POST (`request.get_json()`),
* Zwracanie kodów statusu (200, 201, 404),
* Testowanie serwera trzema klientami: przeglądarką, `curl`, `requests`.

Narzędzia: Python (Flask, `requests`), `curl`, VSCode.

---

# Przygotowanie środowiska

## Przejście na VSCode

Od tego labu pracujemy w **VSCode**. Flask wymaga dwóch procesów jednocześnie (serwer i klient), a VSCode pozwala wygodnie otworzyć kilka terminali obok siebie.

Otwórz VSCode. Utwórz nowy folder roboczy (np. `lab3/`) i otwórz go (`File → Open Folder`).

## Instalacja Flask

Otwórz terminal w VSCode (`Ctrl+`` ` lub `Terminal → New Terminal`):

```bash
pip install flask
```

Sprawdź:

```bash
python -c "import flask; print(flask.__version__)"
```

::: {.callout-tip}
## Instalacja pakietów w pracowni
Komputery w pracowni mogą resetować pakiety między sesjami. Na początku każdego labu sprawdź, czy Flask jest dostępny, i w razie potrzeby zainstaluj go ponownie.
:::

## Workflow: dwa terminale

Praca z serwerem wymaga **dwóch terminali**:

* **Terminal 1 (serwer)** — tu uruchamiasz Flask. Serwer zajmuje terminal, dopóki go nie zatrzymasz (`Ctrl+C`).
* **Terminal 2 (klient)** — tu wysyłasz żądania: `curl`, skrypty Pythona z `requests`, albo otwierasz przeglądarkę.

W VSCode: kliknij ikonę `+` w panelu terminala, żeby otworzyć drugi terminal. Możesz je rozłożyć obok siebie (`Split Terminal`).

## Konwencje

Na tym labie stosujemy stałe konwencje:

* Plik serwera zawsze nazywamy **`app.py`**.
* Serwer uruchamiamy poleceniem:

```bash
flask run --debug -p 5000
```

* `--debug` włącza auto-reload (serwer restartuje się po zmianie kodu) i debugger.
* `-p 5000` ustawia port. Jeśli 5000 jest zajęty, użyj innego (np. `-p 5001`).
* Adres serwera: **`http://localhost:5000`** (lub `http://127.0.0.1:5000`).

::: {.callout-warning}
## Polecenie `flask run` szuka pliku `app.py`
Flask automatycznie ładuje plik o nazwie `app.py` z bieżącego katalogu. Jeśli nazwiesz plik inaczej, musisz ustawić zmienną `FLASK_APP`, np. `FLASK_APP=server.py flask run --debug -p 5000`. Najprostsze rozwiązanie: trzymaj się nazwy `app.py`.
:::

::: {.callout-note}
## Checkpoint
Czy masz otwarty VSCode z dwoma terminalami? Czy `flask --version` zwraca numer wersji?
:::

---

# Demonstracja 1: serwer GET

Utwórz plik `app.py` z następującą treścią:

```python
from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "Strona główna serwera Lab 3"


@app.route("/hello")
def hello():
    return "<h1>Cześć!</h1><p>To jest strona HTML.</p>"


@app.route("/status")
def status():
    return {"server": "lab3", "status": "ok"}
```

W **Terminalu 1** uruchom serwer:

```bash
flask run --debug -p 5000
```

Powinieneś zobaczyć komunikat `Running on http://127.0.0.1:5000`. Serwer działa — nie zamykaj tego terminala.

## Test: trzech klientów

Przetestuj serwer trzema sposobami. W **Terminalu 2**:

**Przeglądarka** — otwórz `http://localhost:5000/`, potem `/hello`, potem `/status`.

**curl:**

```bash
curl http://localhost:5000/
curl http://localhost:5000/hello
curl -i http://localhost:5000/status
```

**Python (requests):**

```python
import requests

r = requests.get("http://localhost:5000/status")
print(r.status_code)
print(r.headers["Content-Type"])
print(r.json())
```

::: {.callout-note}
## Checkpoint
Trasa `/status` zwraca słownik Pythona. Flask automatycznie konwertuje go na JSON i ustawia `Content-Type: application/json`. Sprawdź to za pomocą `curl -i` — czy widzisz `Content-Type: application/json`?
:::

## Co obserwować

Zwróć uwagę na **Terminal 1** (serwer) — Flask loguje każde żądanie:

```
127.0.0.1 - - [15/Mar/2026 10:30:00] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [15/Mar/2026 10:30:05] "GET /hello HTTP/1.1" 200 -
```

Widzisz metodę, ścieżkę i kod statusu. To jest ta sama informacja, którą na Labie 1 obserwowałeś po stronie klienta w `curl -v`.

---

# Demonstracja 2: serwer z GET i POST

Zastąp zawartość `app.py` (auto-reload przeładuje serwer automatycznie):

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

# "Baza danych" — lista w pamięci
messages = []


@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(messages)


@app.route("/messages", methods=["POST"])
def add_message():
    data = request.get_json()

    if not data or "text" not in data:
        return {"error": "Brak pola 'text'"}, 400

    message = {
        "id": len(messages) + 1,
        "text": data["text"],
    }
    messages.append(message)
    return jsonify(message), 201


@app.route("/messages/<int:msg_id>")
def get_message(msg_id):
    for msg in messages:
        if msg["id"] == msg_id:
            return jsonify(msg)
    return {"error": "Nie znaleziono"}, 404
```

## Test: cykl życia wiadomości

W **Terminalu 2** wykonaj po kolei:

**1. Lista (pusta):**

```bash
curl http://localhost:5000/messages
```

Wynik: `[]` — lista jest pusta.

**2. Dodaj wiadomość (POST z JSON):**

```bash
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d '{"text": "Pierwsza wiadomość"}'
```

Wynik: `{"id": 1, "text": "Pierwsza wiadomość"}` z kodem `201`.

**3. Dodaj drugą:**

```bash
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d '{"text": "Druga wiadomość"}'
```

**4. Lista (dwie wiadomości):**

```bash
curl http://localhost:5000/messages
```

**5. Konkretna wiadomość:**

```bash
curl http://localhost:5000/messages/1
```

**6. Nieistniejąca wiadomość:**

```bash
curl -i http://localhost:5000/messages/999
```

Wynik: `404` z `{"error": "Nie znaleziono"}`.

::: {.callout-note}
## Checkpoint
Czy widzisz różnicę między `GET /messages` (lista) a `GET /messages/1` (element)? To jest wzorzec **kolekcja / element** z Wykładu 1 — teraz zaimplementowany po stronie serwera.
:::

## Ten sam test w Pythonie

```python
import requests

BASE = "http://localhost:5000"

# POST — dodaj wiadomość
r = requests.post(
    f"{BASE}/messages",
    json={"text": "Wiadomość z Pythona"},
    timeout=5,
)
print("POST:", r.status_code, r.json())

# GET — pobierz listę
r = requests.get(f"{BASE}/messages", timeout=5)
print("GET:", r.status_code, r.json())
```

Zwróć uwagę: `requests.post(..., json={...})` automatycznie ustawia `Content-Type: application/json` i serializuje słownik — nie musisz tego robić ręcznie (jak w `curl` z `-H` i `-d`).

---

# Ćwiczenia ze szkieletem

## Ćwiczenie 1: routing i query string

Poniżej jest serwer z jednym gotowym endpointem i dwoma do uzupełnienia. Wklej go do `app.py` i uzupełnij miejsca oznaczone komentarzami.

```python
from flask import Flask, request

app = Flask(__name__)

STUDENTS = [
    {"id": 1, "name": "Anna Kowalska", "field": "Informatyka"},
    {"id": 2, "name": "Jan Nowak", "field": "Matematyka"},
    {"id": 3, "name": "Maria Wiśniewska", "field": "Informatyka"},
    {"id": 4, "name": "Piotr Zieliński", "field": "Fizyka"},
    {"id": 5, "name": "Katarzyna Lewandowska", "field": "Matematyka"},
]


@app.route("/")
def index():
    return "Serwer studentów — Lab 3"


@app.route("/students")
def students_list():
    """Zwraca listę studentów.
    
    Opcjonalny parametr ?field=... filtruje po kierunku.
    Bez parametru — zwraca wszystkich.
    """
    field = request.args.get("field")
    
    if field:
        result = [s for s in STUDENTS if s["field"] == field]
    else:
        result = STUDENTS
    
    return {"data": result, "count": len(result)}


# --- Ćwiczenie 1a ---
# Dodaj trasę GET /students/<int:student_id>
# Zwróć dane studenta o podanym id.
# Jeśli nie ma studenta o takim id — zwróć {"error": "Nie znaleziono"}, 404.
# --- Twój kod ---


# --- Ćwiczenie 1b ---
# Dodaj trasę GET /fields
# Zwróć listę unikalnych kierunków studiów (bez powtórzeń).
# Wskazówka: set() + list().
# --- Twój kod ---
```

Przetestuj (po uzupełnieniu):

```bash
curl http://localhost:5000/students
curl "http://localhost:5000/students?field=Informatyka"
curl http://localhost:5000/students/3
curl -i http://localhost:5000/students/99
curl http://localhost:5000/fields
```

::: {.callout-note}
## Checkpoint
Czy `/students?field=Informatyka` zwraca tylko 2 studentów? Czy `/students/99` zwraca kod 404?
:::


## Ćwiczenie 2: POST — dodawanie danych

Rozbuduj serwer studentów o możliwość **dodawania** nowych studentów. Poniżej szkielet — uzupełnij ciało funkcji:

```python
@app.route("/students", methods=["GET", "POST"])
def students_list():
    if request.method == "GET":
        # (istniejący kod filtrowania — przepisz z Ćwiczenia 1)
        ...
    
    elif request.method == "POST":
        # 1. Pobierz dane z ciała żądania: request.get_json()
        # 2. Sprawdź, czy JSON zawiera pola "name" i "field".
        #    Jeśli brakuje — zwróć {"error": "Brak wymaganych pól"}, 400.
        # 3. Utwórz nowy słownik z id (następne po ostatnim),
        #    name i field.
        # 4. Dodaj do listy STUDENTS.
        # 5. Zwróć nowy obiekt z kodem 201.
        # --- Twój kod ---
        ...
```

::: {.callout-tip}
## Wskazówka: nowe id
Nowe `id` możesz obliczyć jako `max(s["id"] for s in STUDENTS) + 1`. Jeśli lista jest pusta, ustaw `1`.
:::

Przetestuj:

```bash
curl -X POST http://localhost:5000/students \
  -H "Content-Type: application/json" \
  -d '{"name": "Tomasz Rodak", "field": "Informatyka"}'

curl http://localhost:5000/students
```

Sprawdź też, co się stanie, gdy wyślesz POST **bez** pola `name`:

```bash
curl -i -X POST http://localhost:5000/students \
  -H "Content-Type: application/json" \
  -d '{"field": "Fizyka"}'
```


## Ćwiczenie 3: HTML z linkami

Napisz serwer, który generuje strony HTML z **listą i podstronami**. Uzupełnij szkielet:

```python
from flask import Flask

app = Flask(__name__)

CITIES = {
    1: {"name": "Warszawa", "population": 1_862_000, "voivodeship": "mazowieckie"},
    2: {"name": "Kraków", "population": 804_000, "voivodeship": "małopolskie"},
    3: {"name": "Łódź", "population": 672_000, "voivodeship": "łódzkie"},
    4: {"name": "Wrocław", "population": 674_000, "voivodeship": "dolnośląskie"},
    5: {"name": "Poznań", "population": 546_000, "voivodeship": "wielkopolskie"},
}


@app.route("/")
def index():
    """Strona główna z linkami do listy miast."""
    return """
    <html><body>
        <h1>Serwer miast</h1>
        <a href="/cities">Lista miast</a>
    </body></html>
    """


@app.route("/cities")
def cities_list():
    """Generuje stronę HTML z listą miast jako linkami.
    
    Każde miasto powinno być linkiem do /cities/<id>.
    """
    # 1. Zbuduj string HTML z nagłówkiem <h1>Miasta</h1>.
    # 2. Dodaj listę <ul>, a w niej dla każdego miasta <li>
    #    z linkiem <a href="/cities/ID">NAZWA</a>.
    # 3. Dodaj link powrotny do strony głównej.
    # --- Twój kod ---
    ...


@app.route("/cities/<int:city_id>")
def city_detail(city_id):
    """Strona szczegółów miasta.
    
    Wyświetla nazwę, liczbę ludności i województwo.
    Zawiera link powrotny do /cities.
    Jeśli miasto nie istnieje — zwróć "Nie znaleziono", 404.
    """
    # --- Twój kod ---
    ...
```

Przetestuj w przeglądarce — klikaj po linkach. Potem przetestuj w `curl`:

```bash
curl http://localhost:5000/cities
curl http://localhost:5000/cities/3
curl -i http://localhost:5000/cities/99
```

::: {.callout-note}
## Checkpoint
Czy w przeglądarce możesz przejść ze strony głównej → lista miast → szczegóły miasta → z powrotem do listy? Struktura stron z linkami to podstawa do crawlingu w Labie 4.
:::

---

# Ćwiczenia samodzielne

## Ćwiczenie A: serwer-kalkulator

Napisz od zera serwer z trasami:

* `GET /add?a=X&b=Y` — zwraca JSON: `{"operation": "add", "a": X, "b": Y, "result": X+Y}`,
* `GET /multiply?a=X&b=Y` — analogicznie dla mnożenia,
* `GET /` — zwraca HTML z opisem dostępnych operacji i przykładowymi linkami (np. `<a href="/add?a=3&b=7">3 + 7</a>`).

Wymagania:

* Parametry `a` i `b` powinny być konwertowane na `float` (użyj `request.args.get("a", type=float)`).
* Jeśli brakuje parametru — zwróć `{"error": "Brak parametru a lub b"}`, 400.

Przetestuj:

```bash
curl "http://localhost:5000/add?a=10&b=3.5"
curl "http://localhost:5000/multiply?a=4&b=7"
curl -i "http://localhost:5000/add?a=10"
```

## Ćwiczenie B: mini-API z CRUD

Napisz od zera serwer przechowujący listę zadań (to-do) w pamięci. Wymagane trasy:

* `GET /tasks` — zwraca listę zadań (JSON),
* `POST /tasks` — dodaje nowe zadanie (JSON w body: `{"title": "..."}`) — zwraca nowe zadanie z `id` i kodem `201`,
* `GET /tasks/<int:task_id>` — zwraca jedno zadanie lub `404`,
* `DELETE /tasks/<int:task_id>` — usuwa zadanie i zwraca `{"deleted": task_id}` lub `404`.

::: {.callout-tip}
## Metoda DELETE
Metoda `DELETE` działa tak samo jak inne — dodaj ją do `methods` i sprawdź `request.method`. Test w curl:
```bash
curl -X DELETE http://localhost:5000/tasks/1
```
:::

Przetestuj pełny cykl: dodaj 3 zadania, wylistuj, pobierz jedno, usuń jedno, wylistuj ponownie.


## Ćwiczenie C: ciąg Collatza

Na wykładzie zobaczyłeś serwer generujący strony HTML dla ciągu Collatza. Teraz napisz go samodzielnie. Przypomnienie reguły:

* jeśli n jest parzyste → następna liczba to n/2,
* jeśli n jest nieparzyste → następna liczba to 3n+1,
* ciąg kończy się, gdy n = 1.

Wymagane trasy:

* `GET /collatz/<int:n>` — strona HTML dla liczby `n`:
    * nagłówek `<h1>` z liczbą,
    * informacja o następnej liczbie w ciągu,
    * link `<a>` do strony następnej liczby (np. `/collatz/5` linkuje do `/collatz/16`),
    * dla `n = 1` — komunikat „Koniec ciągu!" i link do `/collatz/7` (żeby spróbować od nowa).
* `GET /` — strona startowa z kilkoma linkami do różnych liczb (np. 6, 7, 27).

Przetestuj w przeglądarce — kliknij w link i podążaj za ciągiem aż do 1.

Potem przetestuj programowo — pobierz stronę `/collatz/6` za pomocą `requests` i wypisz HTML:

```python
import requests

r = requests.get("http://localhost:5000/collatz/6")
print(r.text)
```

Czy widzisz w HTML-u link do następnej strony? Na Labie 4 napiszemy program, który będzie automatycznie wyciągał te linki i podążał za nimi.

---

# Zadanie dodatkowe

## Zadanie D: serwer z wieloma widokami jednego zbioru danych

Napisz serwer, który przechowuje listę książek:

```python
BOOKS = [
    {"id": 1, "title": "Pan Tadeusz", "author": "Mickiewicz", "year": 1834, "genre": "Epopeja"},
    {"id": 2, "title": "Lalka", "author": "Prus", "year": 1890, "genre": "Powieść"},
    {"id": 3, "title": "Quo Vadis", "author": "Sienkiewicz", "year": 1896, "genre": "Powieść"},
    {"id": 4, "title": "Ferdydurke", "author": "Gombrowicz", "year": 1937, "genre": "Powieść"},
    {"id": 5, "title": "Solaris", "author": "Lem", "year": 1961, "genre": "Science fiction"},
]
```

Wymagane trasy:

* `GET /books` — JSON z listą książek. Opcjonalny parametr `?genre=...` filtruje po gatunku.
* `GET /books/<int:book_id>` — JSON z jedną książką lub 404.
* `GET /catalog` — strona HTML: tabela (`<table>`) ze wszystkimi książkami (kolumny: tytuł, autor, rok). Tytuł każdej książki powinien być linkiem do `/books/<id>`.
* `POST /books` — dodaje nową książkę (JSON w body musi zawierać `title` i `author`; `year` i `genre` opcjonalne).

To ćwiczenie łączy wszystkie elementy z labu: routing, query string, parametry ścieżki, HTML z linkami, JSON, POST, kody statusu.

---

# Podsumowanie

W tym labie:

* skonfigurowałeś środowisko: VSCode, Flask, dwa terminale (serwer + klient),
* napisałeś serwery Flask z trasami GET i POST,
* przetestowałeś serwer trzema klientami (przeglądarka, `curl`, `requests`) — i zobaczyłeś to samo żądanie z trzech perspektyw,
* obsłużyłeś parametry: query string (`request.args`), zmienne trasowe (`<int:...>`), body JSON (`request.get_json()`),
* zwracałeś odpowiedzi w różnych formatach (tekst, HTML, JSON) i z różnymi kodami statusu (200, 201, 400, 404),
* wygenerowałeś strony HTML z linkami — strukturę, po której będziemy nawigować crawlerem.

W następnym labie: piszemy crawlera w `requests`, który automatycznie przechodzi po stronach serwera z tego labu i zbiera dane.