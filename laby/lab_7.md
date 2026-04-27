---
title: "Lab 7: Serwer z sesjami i logowaniem"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Cookies na poziomie nagłówków HTTP — `Set-Cookie` i `Cookie` w surowej postaci,
* Sesje we Flask: `flask.session`, `secret_key`, podpisane cookie,
* Formularz logowania i wzorzec POST → 302 → GET (PRG),
* Kontrola dostępu: 401 (niezalogowany) vs 403 (zalogowany bez uprawnień),
* Dane chronione, widoczne tylko dla właściciela (notatki per-user),
* Inspekcja cookies w DevTools (zakładki Network i Application),
* Diagnoza: dlaczego dwa kolejne wywołania `requests.get` / `requests.post` nie współdzielą sesji.

Narzędzia: Python (Flask, `requests`), przeglądarka z DevTools, VSCode.

---

# Przygotowanie

Środowisko jak na poprzednich labach: VSCode, dwa terminale (serwer + klient), Flask.

Sprawdź, czy Flask jest dostępny:

```bash
pip install flask
```

Utwórz folder `lab7/` i otwórz go w VSCode.

::: {.callout-tip}
## Instalacja pakietów w pracowni
Komputery w pracowni mogą resetować pakiety między sesjami. Na początku każdego labu sprawdź, czy `flask` i `requests` są dostępne, i w razie potrzeby zainstaluj je ponownie.
:::

Na tym labie pracujemy z **jednym plikiem `app.py`**, który będziemy rozbudowywać krok po kroku. Auto-reload Flaska (`--debug`) przeładuje serwer po każdym zapisie.

---

# Demonstracja 1: Cookies bez sesji

Z wykładu wiesz, że cookie to para klucz–wartość, którą serwer prosi klienta o zapamiętanie. Mechanizm działa na poziomie nagłówków HTTP — `Set-Cookie` w odpowiedzi, `Cookie` w kolejnym żądaniu. Zobaczmy to na żywo.

Utwórz plik `app.py`:

```python
from flask import Flask, request, make_response

app = Flask(__name__)


@app.route("/set-name")
def set_name():
    name = request.args.get("name", "Anonim")
    response = make_response(f"Ustawiono cookie: user={name}")
    response.set_cookie("user", name)
    return response


@app.route("/hello")
def hello():
    name = request.cookies.get("user")
    if name is None:
        return "Cześć, nieznajomy! Najpierw wejdź na /set-name?name=Twoje_imie"
    return f"Cześć, {name}!"
```

Uruchom serwer w **Terminalu 1**:

```bash
flask run --debug -p 5000
```

## Test 1: przeglądarka + DevTools

Otwórz `http://127.0.0.1:5000/set-name?name=Jan` w przeglądarce. Następnie otwórz **DevTools** (`F12`).

**Zakładka Network:**

1. Odśwież stronę (`Ctrl+R`) — żądanie pojawi się na liście.
2. Kliknij na żądanie `set-name?name=Jan`.
3. Po prawej stronie wybierz zakładkę **Headers**.
4. W sekcji **Response Headers** zobaczysz: `set-cookie: user=Jan; Path=/`.

To jest dokładnie ten nagłówek, który wykład pokazywał w teorii — teraz widzisz go na żywo.

Teraz przejdź na `http://127.0.0.1:5000/hello`. Strona pokaże `Cześć, Jan!`. W DevTools (Network → wybrane żądanie → Headers):

* w sekcji **Request Headers** zobaczysz: `cookie: user=Jan` — przeglądarka **automatycznie** dosłała cookie, które wcześniej dostała.

**Zakładka Application** (Chrome) lub **Storage** (Firefox):

1. Po lewej rozwiń **Cookies** → `http://127.0.0.1:5000`.
2. Zobaczysz wiersz: `user` = `Jan`.

To jest cookie jar przeglądarki — lokalna pamięć, w której są wszystkie cookies dla tej domeny.

::: {.callout-note}
## Checkpoint
1. Czy w Response Headers żądania `/set-name` widzisz `set-cookie: user=Jan`?
2. Czy w Request Headers żądania `/hello` widzisz `cookie: user=Jan`?
3. Czy w zakładce Application → Cookies widnieje wpis `user=Jan`?
:::

## Test 2: Python + `requests`

Utwórz plik `test_cookies.py` w **Terminalu 2**:

```python
import requests

# 1. Pierwsze żądanie — serwer ustawia cookie
r1 = requests.get("http://127.0.0.1:5000/set-name", params={"name": "Jan"})
print("Status:", r1.status_code)
print("Set-Cookie nagłówek:", r1.headers.get("Set-Cookie"))
print("Cookies w odpowiedzi:", r1.cookies.get_dict())

# 2. Drugie żądanie — sprawdźmy, czy cookie zostało zapamiętane
r2 = requests.get("http://127.0.0.1:5000/hello")
print("\nDrugie żądanie:")
print("Treść:", r2.text)
```

Uruchom:

```bash
python test_cookies.py
```

Spodziewany efekt:

```
Status: 200
Set-Cookie nagłówek: user=Jan; Path=/
Cookies w odpowiedzi: {'user': 'Jan'}

Drugie żądanie:
Treść: Cześć, nieznajomy! Najpierw wejdź na /set-name?name=Twoje_imie
```

Zwróć uwagę: pierwsze żądanie **dostało** cookie, ale drugie żądanie go **nie wysłało**. To jest dokładnie różnica między przeglądarką a `requests.get`: przeglądarka utrzymuje cookie jar między żądaniami, gołe `requests.get` — nie. Wrócimy do tego w Ćwiczeniu 3.

::: {.callout-note}
## Checkpoint
1. Czy `r1.cookies.get_dict()` zwraca `{'user': 'Jan'}`?
2. Dlaczego `r2.text` nie zawiera imienia, mimo że `r1` ustawiło cookie?
:::

---

# Demonstracja 2: Sesja Flask

Cookie z Demo 1 ma dwa problemy:

* klient może je dowolnie modyfikować (otwórz DevTools → Application → kliknij dwukrotnie na wartość `user=Jan` i zmień na `user=admin` — odśwież stronę),
* nie nadaje się do przechowywania większych ani wrażliwych danych.

Flask rozwiązuje to przez `flask.session` — dane sesji są zapisywane w cookie, ale **podpisane kryptograficznie** kluczem serwera.

Zastąp zawartość `app.py` (auto-reload przeładuje serwer):

```python
from flask import Flask, session

app = Flask(__name__)
app.secret_key = "klucz-tylko-do-labu"


@app.route("/login-quick")
def login_quick():
    session["user"] = "Jan"
    return "Zalogowano jako Jan! Wejdź na /profile"


@app.route("/profile")
def profile():
    user = session.get("user")
    if not user:
        return "Nie jesteś zalogowany.", 401
    return f"Profil użytkownika: {user}"


@app.route("/logout")
def logout():
    session.clear()
    return "Wylogowano. Wejdź na /profile, żeby zobaczyć efekt."
```

## Test: przeglądarka + DevTools

Otwórz `http://127.0.0.1:5000/login-quick`, potem `/profile`. Działa.

Otwórz DevTools → **Application** → Cookies. Zobaczysz cookie o nazwie `session` z wartością, która wygląda mniej więcej tak:

```
.eJyrViouSc3PVbJSyihJzVUoSczNykzMqVRSqAUAOOoIPg.aFcZxA.XYZ...
```

To są dane sesji (`{"user": "Jan"}`) zakodowane w base64, plus podpis na końcu. Klient widzi treść, ale nie może jej zmienić bez znajomości `secret_key`.

**Test podpisu** — spróbuj sfałszować cookie:

1. W DevTools → Application → Cookies kliknij dwukrotnie na wartość cookie `session`.
2. Zmień jeden znak na końcu (np. ostatnią literę).
3. Wejdź na `/profile`.

Wynik: dostajesz `Nie jesteś zalogowany. (401)`. Flask sprawdził podpis, podpis się nie zgadza, więc cookie zostało odrzucone — sesja jest pusta, jakbyś się nigdy nie zalogował.

Wejdź na `/login-quick` jeszcze raz, żeby przywrócić sesję, a potem na `/logout`. Sprawdź `/profile` — znowu 401. To są trzy stany sesji: zalogowany, sfałszowany, wylogowany.

::: {.callout-note}
## Checkpoint
1. Czy widzisz w DevTools cookie `session` z długą zakodowaną wartością?
2. Po sfałszowaniu cookie — czy `/profile` zwraca 401?
3. Po `/logout` — czy cookie znika z DevTools (lub przyjmuje wartość pustą)?
:::

::: {.callout-warning}
## `secret_key` to nie hasło użytkownika
`secret_key` to klucz **serwera** — używany do podpisywania wszystkich sesji. Hasła użytkowników to osobna sprawa (pojawią się w Demo 3). W produkcji `secret_key` musi być długi, losowy i nigdy nie commitowany do repozytorium. W laboratorium używamy dowolnego stringa.
:::

---

# Demonstracja 3: Pełny formularz logowania

Demo 2 logowało użytkownika przez `GET /login-quick` — to nie jest realistyczne. W prawdziwych aplikacjach logowanie odbywa się przez **formularz HTML** z polami login i hasło, wysyłany metodą POST.

Zastąp zawartość `app.py`:

```python
from flask import Flask, request, session, redirect

app = Flask(__name__)
app.secret_key = "klucz-tylko-do-labu"

# Baza użytkowników (w produkcji: prawdziwa baza + hashowane hasła)
USERS = {
    "admin": "secret",
    "jan": "haslo123",
    "anna": "qwerty",
}

LOGIN_PAGE = """
<!doctype html>
<html>
<body>
    <h1>Logowanie</h1>
    {message}
    <form action="/login" method="POST">
        <p><label>Login: <input type="text" name="username"></label></p>
        <p><label>Hasło: <input type="password" name="password"></label></p>
        <p><button type="submit">Zaloguj</button></p>
    </form>
</body>
</html>
"""

DASHBOARD_PAGE = """
<!doctype html>
<html>
<body>
    <h1>Panel użytkownika</h1>
    <p>Zalogowany jako: <b>{user}</b></p>
    <p>To jest chroniona strona — widoczna tylko po zalogowaniu.</p>
    <p><a href="/logout">Wyloguj</a></p>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return LOGIN_PAGE.format(message="")

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if USERS.get(username) == password:
        session["user"] = username
        return redirect("/dashboard")

    return LOGIN_PAGE.format(
        message='<p style="color:red">Błędny login lub hasło.</p>'
    ), 401


@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect("/login")
    return DASHBOARD_PAGE.format(user=user)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
```

## Test: przeglądarka

Otwórz `http://127.0.0.1:5000/dashboard`. Bez sesji jesteś przekierowany na `/login` — zobacz formularz.

Wpisz `jan` / `haslo123`, kliknij **Zaloguj**. Trafiasz na `/dashboard` z napisem `Zalogowany jako: jan`.

Otwórz DevTools → **Network** i powtórz logowanie (najpierw `/logout`). Zobaczysz w panelu Network ciąg trzech żądań:

1. `POST /login` → status `302 FOUND`, w odpowiedzi nagłówek `Location: /dashboard`,
2. `GET /dashboard` → status `200 OK` (przeglądarka automatycznie podąża za przekierowaniem),
3. (ewentualnie) statyczne zasoby strony.

To jest wzorzec **POST → redirect → GET** (PRG): formularz wysyła POST, serwer zapisuje stan i zwraca 302, przeglądarka pobiera GET-em wynikową stronę. Dzięki temu odświeżenie `/dashboard` nie wysyła ponownie formularza logowania.

W **Terminalu 1** (serwer) zobaczysz ten sam przepływ w logach:

```
127.0.0.1 - - [25/Apr/2026 10:30:00] "POST /login HTTP/1.1" 302 -
127.0.0.1 - - [25/Apr/2026 10:30:00] "GET /dashboard HTTP/1.1" 200 -
```

::: {.callout-note}
## Checkpoint
1. Czy formularz `/login` z poprawnymi danymi przekierowuje na `/dashboard`?
2. Czy formularz z błędnymi danymi zwraca 401 i pokazuje czerwony komunikat?
3. Czy w DevTools → Network widzisz parę: POST 302, potem GET 200?
4. Czy `/logout` czyści sesję — `/dashboard` znowu przekierowuje na `/login`?
:::

::: {.callout-tip}
## `request.form` vs `request.args` vs `request.get_json()`
Flask udostępnia trzy źródła danych żądania:

* `request.args` — query string z URL-a (`?key=value`),
* `request.form` — body POST z `Content-Type: application/x-www-form-urlencoded` (formularz HTML),
* `request.get_json()` — body POST z `Content-Type: application/json` (API z Labu 3).

Formularz HTML wysyła `application/x-www-form-urlencoded`, dlatego serwer odczytuje dane przez `request.form`.
:::

---

# Ćwiczenie 1: panel administratora (401 vs 403)

Z wykładu wiesz, że dwa różne kody statusu opisują dwa różne problemy z dostępem:

* **401 Unauthorized** — klient nie jest uwierzytelniony (nie zalogowany),
* **403 Forbidden** — klient jest uwierzytelniony, ale nie ma uprawnień.

W tym ćwiczeniu dodasz endpoint `/admin`, który widzi tylko użytkownik o loginie `admin`.

## Zadanie

Rozszerz `app.py` z Demo 3 o nowy endpoint `/admin`:

* jeśli użytkownik nie jest zalogowany → zwróć **401**,
* jeśli zalogowany, ale to nie `admin` → zwróć **403**,
* jeśli zalogowany jako `admin` → zwróć stronę HTML z napisem `Panel administratora — witaj, admin!`.

Uzupełnij szkielet:

```python
from flask import abort

ADMIN_PAGE = """
<!doctype html>
<html>
<body>
    <h1>Panel administratora</h1>
    <p>Witaj, <b>{user}</b>! To jest strona widoczna tylko dla admina.</p>
    <p><a href="/dashboard">Wróć do panelu</a> | <a href="/logout">Wyloguj</a></p>
</body>
</html>
"""


@app.route("/admin")
def admin_panel():
    user = session.get("user")
    # 1. Jeśli niezalogowany — zwróć 401.
    # --- Twój kod ---

    # 2. Jeśli zalogowany, ale nie jest adminem — zwróć 403.
    # --- Twój kod ---

    # 3. Jeśli admin — zwróć ADMIN_PAGE.
    # --- Twój kod ---
```

::: {.callout-tip}
## `abort()` we Flask
`abort(401)` i `abort(403)` to wygodny skrót: Flask sam zwróci odpowiedni kod statusu i prostą stronę błędu. Możesz też pisać `return "...", 401` jak w Demo 3 — efekt jest taki sam, kwestia stylu.
:::

## Test

Wykonaj trzy scenariusze, każdy w osobnym oknie/karcie przeglądarki **incognito** (żeby ciasteczka się nie nakładały):

1. **Niezalogowany** — wejdź bezpośrednio na `/admin`. Oczekiwane: strona błędu 401.
2. **Zalogowany jako `jan`** — zaloguj się formularzem, potem `/admin`. Oczekiwane: strona błędu 403.
3. **Zalogowany jako `admin`** — wyloguj się, zaloguj jako `admin`, potem `/admin`. Oczekiwane: panel administratora.

::: {.callout-note}
## Checkpoint
1. Czy każdy z trzech scenariuszy zwraca odpowiedni kod statusu (sprawdź w DevTools → Network)?
2. Czy w terminalu serwera widzisz w logach `... "GET /admin HTTP/1.1" 401`, `... 403`, `... 200`?
3. Co by się stało, gdybyś w punkcie 2 sprawdzał najpierw rolę, a dopiero potem zalogowanie? Wpadłbyś w `KeyError` na `session["user"]` — kolejność warunków ma znaczenie.
:::

---

# Ćwiczenie 2: notatki per-user

Sesja to nie tylko „zalogowany / nie zalogowany" — to przede wszystkim **tożsamość żądania**. Serwer wie, kto pyta, więc może zwracać dane przypisane do konkretnego użytkownika.

W tym ćwiczeniu dodasz funkcję notatek: każdy zalogowany użytkownik widzi i dodaje **wyłącznie własne** notatki. Notatki innych użytkowników są dla niego niewidoczne.

## Zadanie

Dodaj do `app.py`:

```python
# Notatki — słownik: login → lista notatek tego użytkownika.
# Każda notatka to po prostu string.
NOTES = {
    "admin": ["TODO: zrobić backup bazy", "Spotkanie z zespołem w piątek"],
    "jan": ["Kupić mleko", "Zadzwonić do mamy", "Oddać książkę do biblioteki"],
    "anna": [],
}

NOTES_PAGE = """
<!doctype html>
<html>
<body>
    <h1>Notatki użytkownika {user}</h1>
    <ul>
        {notes_html}
    </ul>
    <h2>Dodaj notatkę</h2>
    <form action="/notes" method="POST">
        <p><input type="text" name="text" size="50" required></p>
        <p><button type="submit">Dodaj</button></p>
    </form>
    <p><a href="/dashboard">Panel</a> | <a href="/logout">Wyloguj</a></p>
</body>
</html>
"""


@app.route("/notes", methods=["GET", "POST"])
def notes():
    user = session.get("user")
    if not user:
        return redirect("/login")

    if request.method == "POST":
        # 1. Pobierz tekst notatki z formularza.
        # --- Twój kod ---

        # 2. Dodaj notatkę do listy użytkownika.
        # --- Twój kod ---

        # 3. Przekierowanie na GET /notes (wzorzec PRG).
        # --- Twój kod ---

    # GET: wyświetl notatki tylko tego użytkownika.
    user_notes = NOTES.get(user, [])
    notes_html = "\n".join(f"<li>{n}</li>" for n in user_notes)
    if not notes_html:
        notes_html = "<li><i>Brak notatek.</i></li>"

    return NOTES_PAGE.format(user=user, notes_html=notes_html)
```

## Test

Wykonaj scenariusz w trzech oknach incognito:

1. **Jako `jan`** — wejdź na `/notes`. Powinieneś zobaczyć trzy notatki Jana. Dodaj nową przez formularz. Pojawi się na liście (po przekierowaniu PRG).
2. **Jako `anna`** — wyloguj `jan`, zaloguj `anna`. Powinnaś zobaczyć **pustą** listę (`Brak notatek.`). Dodaj notatkę. Pojawi się tylko ta jedna.
3. **Jako `admin`** — wyloguj, zaloguj `admin`. Powinieneś zobaczyć tylko notatki admina (`TODO: zrobić backup bazy` i drugą). Notatek Jana ani Anny **nie widzisz**.

To jest istota sesji: ten sam endpoint `/notes` zwraca **inne dane** w zależności od tego, kto pyta. Serwer rozpoznaje klienta po `session["user"]`.

::: {.callout-note}
## Checkpoint
1. Czy `jan` widzi tylko swoje notatki?
2. Czy po dodaniu notatki przez Jana, Anna jej nie widzi?
3. Czy formularz dodawania notatki działa wzorcem PRG (POST → 302 → GET)? Sprawdź w DevTools → Network.
4. Co by się stało, gdyby zamiast `NOTES.get(user, [])` napisać `NOTES[user]`? Spróbuj — który użytkownik wywoła `KeyError`? (Wskazówka: `anna` ma pustą listę, więc nie. Ale gdyby pojawił się czwarty user…)
:::

::: {.callout-warning}
## Notatki giną po zatrzymaniu serwera
`NOTES` to zwykły słownik w pamięci procesu. Gdy zatrzymasz serwer (`Ctrl+C`) i uruchomisz go ponownie, wszystkie dodane notatki znikną — wrócisz do stanu początkowego. To celowe uproszczenie: lab dotyczy sesji, nie trwałego przechowywania danych.
:::

---

# Ćwiczenie 3: dlaczego `requests.get` nie wystarcza

Demo 1 pokazało, że dwa kolejne wywołania `requests.get` nie współdzielą cookies. Sprawdźmy, jakie są tego konsekwencje przy próbie programowego zalogowania się do naszego serwera.

## Zadanie

Utwórz plik `bezsesji.py`:

```python
import requests

BASE = "http://127.0.0.1:5000"

# 1. Logowanie — POST z danymi formularza.
print("=== Krok 1: logowanie ===")
r1 = requests.post(
    f"{BASE}/login",
    data={"username": "jan", "password": "haslo123"},
    allow_redirects=False,  # Zatrzymaj się na 302, żeby zobaczyć cookie
)
print(f"Status: {r1.status_code}")
print(f"Location: {r1.headers.get('Location')}")
print(f"Cookies w odpowiedzi: {r1.cookies.get_dict()}")

# 2. Próba pobrania chronionej strony — osobne wywołanie.
print("\n=== Krok 2: próba pobrania /notes ===")
r2 = requests.get(f"{BASE}/notes", allow_redirects=False)
print(f"Status: {r2.status_code}")
print(f"Location: {r2.headers.get('Location')}")
print(f"Cookies wysłane do serwera: {r2.request.headers.get('Cookie')}")

# 3. Próba pobrania panelu administratora.
print("\n=== Krok 3: próba pobrania /admin ===")
r3 = requests.get(f"{BASE}/admin", allow_redirects=False)
print(f"Status: {r3.status_code}")
```

Uruchom:

```bash
python bezsesji.py
```

## Co widzimy?

Spodziewany wynik:

```
=== Krok 1: logowanie ===
Status: 302
Location: /dashboard
Cookies w odpowiedzi: {'session': '.eJyrViou...'}

=== Krok 2: próba pobrania /notes ===
Status: 302
Location: /login
Cookies wysłane do serwera: None

=== Krok 3: próba pobrania /admin ===
Status: 401
```

Zwróć uwagę:

* **Krok 1**: logowanie powiodło się. Serwer odpowiedział 302 z cookie sesyjnym w `Set-Cookie`. `r1.cookies` widzi to cookie.
* **Krok 2**: `requests.get` wykonane na nowo — **nie ma cookies**. `r2.request.headers.get('Cookie')` zwraca `None`. Serwer widzi żądanie bez sesji, więc przekierowuje na `/login`.
* **Krok 3**: również brak cookies. Serwer zwraca 401.

Mimo że krok 1 dostał poprawne cookie, kroki 2 i 3 go **nie wysłały**. Każde wywołanie `requests.get` / `requests.post` jest niezależnym żądaniem HTTP, bez żadnej pamięci o poprzednich.

::: {.callout-note}
## Checkpoint
1. Czy krok 1 zwraca status 302 i niepuste `r1.cookies`?
2. Czy w kroku 2 `r2.request.headers.get('Cookie')` zwraca `None`?
3. Co by się stało, gdybyś w kroku 1 ustawił `allow_redirects=True` (domyślne)? Spróbuj — `r1.url` pokaże, że klient podążył za przekierowaniem na `/dashboard`, ale na **drugie** wywołanie `requests.get` cookie i tak nie dotrze.
:::

::: {.callout-tip}
## `allow_redirects=False` w diagnostyce
Domyślnie `requests` automatycznie podąża za 302 (jak przeglądarka). To wygodne przy normalnym scrapingu, ale ukrywa, co dokładnie dzieje się przy logowaniu. `allow_redirects=False` zatrzymuje klienta na pierwszej odpowiedzi, dzięki czemu widzisz nagłówek `Location` i `Set-Cookie` zwrócone bezpośrednio przez endpoint logowania.
:::

---

# Podsumowanie

W tym labie:

* zobaczyłeś `Set-Cookie` i `Cookie` w surowej postaci — w DevTools (Network → Headers) i w Pythonie (`r.headers`, `r.cookies`),
* zbudowałeś serwer z sesją Flask: `secret_key`, `session["user"]`, `session.clear()`,
* napisałeś endpoint logowania ze wzorcem **POST → redirect → GET** i obsługą formularza HTML (`request.form`),
* rozróżniłeś **401** (niezalogowany) od **403** (zalogowany bez uprawnień) na żywym kodzie,
* zaimplementowałeś dane chronione i prywatne — `/notes`, gdzie ten sam endpoint zwraca inne dane różnym użytkownikom,
* zdiagnozowałeś, dlaczego dwa wywołania `requests.get` / `requests.post` nie współdzielą sesji.

Twój serwer ma teraz endpointy: `/login` (GET+POST), `/logout`, `/dashboard`, `/admin`, `/notes` (GET+POST). Trzymaj go w folderze `lab7/` — będzie celem klienta na Lab 8.

**Co dalej:**

* **Lab 8**: piszesz klienta w `requests.Session`, który automatycznie utrzymuje cookies między żądaniami. Zaloguje się on do serwera z tego labu i zescrapuje notatki różnych użytkowników. Ostatnie ćwiczenie tego labu (`bezsesji.py`) zostanie naprawione w jednej linijce.
