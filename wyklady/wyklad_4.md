---
title: "Wykład 4: Cookies, sesje i formularze"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

## Cele i zakres

Na poprzednich wykładach nauczyliśmy się budować serwery Flask, parsować HTML i wyciągać z niego dane. Brakowało jednak jednego elementu: **stanu**. Serwery, które budowaliśmy, traktowały każde żądanie identycznie — nie rozróżniały klientów. Teraz zobaczymy, jak serwer „zapamiętuje" klienta między żądaniami i jak to wykorzystać w scrapingu.

Zakres obejmuje:

* bezstanowość HTTP — dlaczego serwer nie pamięta klienta,
* cookies — mechanizm na poziomie nagłówków HTTP (`Set-Cookie` / `Cookie`),
* sesje — dane przechowywane na serwerze, identyfikowane przez cookie,
* formularze HTML — jak przeglądarka wysyła dane POST (kontrast z JSON API z Labu 3),
* `requests.Session` — automatyczne utrzymywanie cookies w kliencie programowym,
* kody 401 i 403 — kontrola dostępu z perspektywy scrapingu.

---

## HTTP jest bezstanowy

Na Wykładzie 1 wspomnieliśmy, że HTTP jest protokołem **bezstanowym**: serwer przetwarza każde żądanie niezależnie i nie przechowuje informacji o wcześniejszych żądaniach tego samego klienta. Dwa kolejne żądania od tego samego klienta są dla serwera nierozróżnialne.

Rozważmy prosty serwer z Labu 3:

```python
@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(messages)
```

Ten endpoint zwraca tę samą listę wiadomości niezależnie od tego, kto pyta. Nie ma pojęcia „zalogowany użytkownik" ani „Twoje wiadomości". Każdy klient widzi to samo.

W praktyce wiele stron wymaga jednak rozróżniania klientów. Przykłady:

* sklep internetowy musi wiedzieć, co jest w **Twoim** koszyku,
* serwis bankowy musi wiedzieć, że **Ty** jesteś zalogowany,
* formularz wyszukiwania zapamiętuje **Twoje** ostatnie zapytanie.

Skoro HTTP nie przechowuje stanu, potrzebujemy mechanizmu, który ten stan doda. Tym mechanizmem są **cookies**.

---

## Cookies — mechanizm HTTP

### Czym jest cookie

Cookie to para klucz–wartość, którą serwer prosi klienta o zapamiętanie. Mechanizm działa na poziomie **nagłówków HTTP** — nie wymaga żadnych specjalnych protokołów ani rozszerzeń:

1. Serwer wysyła w odpowiedzi nagłówek `Set-Cookie: klucz=wartość`.
2. Klient (przeglądarka, `requests.Session`, `curl -b`) zapamiętuje tę parę.
3. Przy następnym żądaniu do tego serwera klient automatycznie dołącza nagłówek `Cookie: klucz=wartość`.

Serwer „rozpoznaje" klienta, bo klient sam odsyła wcześniej otrzymane cookie.

### Przepływ: Set-Cookie i Cookie

Zobaczmy to na konkretnym scenariuszu — serwer ustawia cookie z imieniem użytkownika:

```
Żądanie 1:
  Klient  →  GET /set-name?name=Jan        →  Serwer
  Klient  ←  200 OK                         ←  Serwer
              Set-Cookie: user=Jan

Żądanie 2:
  Klient  →  GET /hello                     →  Serwer
              Cookie: user=Jan
  Klient  ←  200 OK                         ←  Serwer
              "Witaj, Jan!"
```

Między żądaniem 1 a 2 serwer nie przechowuje żadnej informacji o kliencie. Cała „pamięć" leży po stronie klienta — w cookie.

### Demo Flask: ustawianie i odczytywanie cookies

```python
from flask import Flask, request, make_response

app = Flask(__name__)


@app.route("/set-name")
def set_name():
    name = request.args.get("name", "Anonim")
    resp = make_response(f"Cookie ustawione dla: {name}")
    resp.set_cookie("user", name)
    return resp


@app.route("/hello")
def hello():
    name = request.cookies.get("user", "nieznany")
    return f"Witaj, {name}!"


@app.route("/delete-name")
def delete_name():
    resp = make_response("Cookie usunięte.")
    resp.delete_cookie("user")
    return resp
```

Testujemy w `curl -v`, żeby zobaczyć nagłówki:

```bash
# Żądanie 1: ustawiamy cookie
curl -v http://localhost:5000/set-name?name=Jan 2>&1 | grep -i "set-cookie"
# < Set-Cookie: user=Jan; Path=/

# Żądanie 2: wysyłamy cookie ręcznie
curl -v -H "Cookie: user=Jan" http://localhost:5000/hello
# Witaj, Jan!

# Żądanie 3: bez cookie
curl http://localhost:5000/hello
# Witaj, nieznany!
```

Nagłówek `Set-Cookie` to zwykły nagłówek odpowiedzi — nic magicznego. Nagłówek `Cookie` to zwykły nagłówek żądania. Przeglądarka obsługuje ten mechanizm automatycznie; w `curl` musimy podać cookie ręcznie (albo użyć `-c`/`-b` do zapisu i odczytu z pliku).

### Atrybuty cookies

Nagłówek `Set-Cookie` może zawierać dodatkowe atrybuty, które kontrolują zachowanie cookie:

| Atrybut | Znaczenie |
|---|---|
| `Path=/` | Cookie wysyłane tylko do ścieżek zaczynających się od `/` (domyślnie: ścieżka, z której przyszła odpowiedź) |
| `Expires=...` / `Max-Age=...` | Czas życia cookie. Bez tego atrybutu cookie jest **sesyjne** — znika po zamknięciu przeglądarki |
| `HttpOnly` | Cookie niedostępne z JavaScript (`document.cookie`). Chroni przed kradzieżą cookie przez XSS |
| `Secure` | Cookie wysyłane tylko przez HTTPS |

Dla scrapingu najważniejsze jest rozróżnienie: **cookie sesyjne** (bez `Expires`) żyje do zamknięcia sesji klienta, a **cookie trwałe** (z `Expires`) przeżywa restart.

---

## Sesje — stan po stronie serwera

### Problem: dane w cookie

Cookie przechowuje dane po stronie klienta. To ma dwie konsekwencje:

1. **Bezpieczeństwo**: klient może dowolnie modyfikować cookie. Jeśli przechowujesz `role=admin` w cookie, użytkownik może to zmienić na `role=superadmin`.
2. **Rozmiar**: przeglądarki ograniczają cookie do ok. 4 KB. Nie zmieścisz tam koszyka zakupowego.

Rozwiązanie: przechowuj dane **na serwerze**, a w cookie trzymaj tylko **identyfikator sesji** — krótki, losowy ciąg znaków, który serwer kojarzy z danymi konkretnego klienta.

```
Cookie: session=a1b2c3d4e5f6
                 │
                 ▼
Serwer: {"a1b2c3d4e5f6": {"user": "Jan", "cart": [...]}}
```

Klient nie widzi ani nie może zmienić danych sesji — zna tylko identyfikator.

### `flask.session`

Flask ma wbudowane wsparcie dla sesji. Technicznie Flask przechowuje dane sesji **w samym cookie**, ale podpisuje je kryptograficznie — klient może je odczytać (to tylko base64), ale nie może ich zmodyfikować bez znajomości klucza:

```python
from flask import Flask, session, redirect

app = Flask(__name__)
app.secret_key = "klucz-tylko-do-labu"  # wymagany do podpisywania sesji


@app.route("/login-quick")
def login_quick():
    session["user"] = "Jan"
    return "Zalogowano jako Jan!"


@app.route("/profile")
def profile():
    user = session.get("user")
    if not user:
        return "Nie jesteś zalogowany.", 401
    return f"Profil użytkownika: {user}"


@app.route("/logout")
def logout():
    session.clear()
    return "Wylogowano."
```

`secret_key` jest wymagany — bez niego Flask nie może podpisać cookie sesyjnego i zgłosi błąd. W labach używamy dowolnego stringa; na produkcji klucz musi być długi i losowy.

### DevTools: podgląd cookies

Po wejściu na `http://localhost:5000/login-quick` w przeglądarce:

1. Otwórz DevTools (`F12`).
2. Zakładka **Application** (Chrome) lub **Storage** (Firefox).
3. W lewym panelu: **Cookies** → `http://localhost:5000`.
4. Zobaczysz cookie o nazwie `session` z wartością, która wygląda jak długi ciąg znaków (to zakodowane i podpisane dane sesji).

Możesz spróbować zmienić wartość cookie w DevTools i odświeżyć stronę — Flask odrzuci zmodyfikowane cookie (podpis się nie zgadza) i potraktuje klienta jako niezalogowanego. To jest efekt `secret_key`.

---

## Formularze HTML — POST z przeglądarki

### JSON API vs formularz HTML

Na Labie 3 wysyłaliśmy POST z danymi JSON:

```bash
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d '{"text": "Wiadomość"}'
```

Serwer odbierał dane przez `request.get_json()`, a klient Pythonowy używał `requests.post(..., json={...})`. To jest wzorzec **JSON API** — programy rozmawiają z programami.

Ale kiedy **człowiek** wpisuje login i hasło w przeglądarce, mechanizm jest inny. Przeglądarka nie wysyła JSON-a — wysyła dane z **formularza HTML**:

| | JSON API (Lab 3) | Formularz HTML |
|---|---|---|
| Content-Type | `application/json` | `application/x-www-form-urlencoded` |
| Format body | `{"username": "Jan"}` | `username=Jan&password=secret` |
| Serwer (Flask) | `request.get_json()` | `request.form["username"]` |
| Klient (requests) | `json={...}` | `data={...}` |
| Klient (przeglądarka) | wymaga JavaScript | `<form>` — natywnie |

Rozróżnienie `data={}` (formularz) vs `json={}` (JSON API) w `requests.post()` to jeden z najczęstszych punktów potknięcia przy scrapingu stron z logowaniem.

### Anatomia formularza

```html
<form action="/login" method="POST">
    <input type="text" name="username">
    <input type="password" name="password">
    <button type="submit">Zaloguj</button>
</form>
```

Trzy kluczowe atrybuty:

* `action="/login"` — URL, do którego przeglądarka wyśle żądanie,
* `method="POST"` — metoda HTTP (domyślnie `GET`, ale przy logowaniu zawsze `POST`),
* `name="username"` — klucze w body żądania. Po kliknięciu „Zaloguj" przeglądarka wyśle: `username=Jan&password=secret`.

### Demo Flask: formularz logowania

Poniższy serwer łączy formularz, sesję i kontrolę dostępu w jeden spójny przepływ. Szablon HTML definiujemy jako string Pythona poza funkcją — to daje separację treści od logiki bez wprowadzania systemu szablonów:

```python
from flask import Flask, request, session, redirect

app = Flask(__name__)
app.secret_key = "klucz-tylko-do-labu"

# Dane użytkowników (w praktyce: baza danych)
USERS = {"admin": "secret", "jan": "haslo123"}

LOGIN_PAGE = """
<html>
<body>
    <h1>Logowanie</h1>
    {message}
    <form action="/login" method="POST">
        <label>Login: <input type="text" name="username"></label><br>
        <label>Hasło: <input type="password" name="password"></label><br>
        <button type="submit">Zaloguj</button>
    </form>
</body>
</html>
"""

DASHBOARD_PAGE = """
<html>
<body>
    <h1>Panel użytkownika</h1>
    <p>Zalogowany jako: {user}</p>
    <p>To jest chroniona strona — widoczna tylko po zalogowaniu.</p>
    <a href="/logout">Wyloguj</a>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return LOGIN_PAGE.format(message="")

    username = request.form["username"]
    password = request.form["password"]

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

Przepływ wygląda tak:

1. `GET /login` — serwer zwraca stronę z formularzem.
2. Użytkownik wypełnia formularz i klika „Zaloguj".
3. Przeglądarka wysyła `POST /login` z `username=admin&password=secret` w body.
4. Serwer sprawdza dane. Jeśli poprawne → ustawia `session["user"]` i przekierowuje (`302`) na `/dashboard`.
5. Przeglądarka podąża za przekierowaniem: `GET /dashboard` — teraz z cookie sesyjnym.
6. Serwer widzi cookie, odczytuje sesję, zwraca chronioną stronę.

Wzorzec **POST → redirect → GET** (PRG) to standardowa praktyka: po udanym logowaniu serwer przekierowuje, żeby odświeżenie strony nie wysłało formularza ponownie.

Realne strony z formularzami często dodają **ukryty token CSRF** — dodatkowe pole `<input type="hidden" name="csrf_token" value="...">`, które zabezpiecza przed wysłaniem formularza z obcej strony. Przy scrapingu oznacza to, że przed POST-em trzeba najpierw pobrać formularz GET-em i wyciągnąć token z HTML-a.

---

## `requests.Session` — klient z pamięcią

### Problem: `requests.get` nie pamięta cookies

Zwykłe wywołania `requests.get()` i `requests.post()` nie przechowują cookies między żądaniami. Każde żądanie jest „czyste":

```python
import requests

# Logujemy się...
requests.post("http://localhost:5000/login",
              data={"username": "admin", "password": "secret"})

# ...ale to żądanie nie ma cookie sesyjnego — serwer nie wie, że się logowaliśmy
r = requests.get("http://localhost:5000/dashboard")
# Dostajemy redirect na /login, bo brak sesji
```

To jest dokładnie bezstanowość HTTP w akcji — dwa osobne wywołania `requests` nie współdzielą żadnego stanu.

### `requests.Session()`

`requests.Session` to obiekt, który **automatycznie zarządza cookies** między żądaniami — tak jak przeglądarka:

```python
import requests

s = requests.Session()

# 1. Logowanie — POST z danymi formularza
r = s.post("http://localhost:5000/login",
           data={"username": "admin", "password": "secret"})
print(r.status_code)  # 200 (po redirect na /dashboard)
print(r.url)          # http://localhost:5000/dashboard

# 2. Pobranie chronionej strony — cookie już jest w sesji
r = s.get("http://localhost:5000/dashboard")
print(r.text)         # "Zalogowany jako: admin"

# 3. Inspekcja cookies
print(s.cookies.get_dict())  # {'session': '...'}
```

Kluczowy szczegół: `data={"username": "admin", "password": "secret"}` — nie `json={}`. Formularz HTML wysyła `application/x-www-form-urlencoded`, więc klient musi zrobić to samo. Użycie `json={}` wyśle `Content-Type: application/json`, a serwer oczekujący `request.form` nie znajdzie danych.

### `curl` z cookies

`curl` ma analogiczny mechanizm — pliki cookie:

```bash
# Logowanie: zapisz cookies do pliku
curl -v -c cookies.txt -L \
  -d "username=admin&password=secret" \
  http://localhost:5000/login

# Pobranie chronionej strony: użyj zapisanych cookies
curl -b cookies.txt http://localhost:5000/dashboard
```

Flagi `-c` (zapisz cookies) i `-b` (wyślij cookies) działają razem. Flaga `-L` podąża za przekierowaniami (POST → 302 → GET).

### Wzorzec: scraping strony z logowaniem

Podsumowując, pełny wzorzec scrapingu strony wymagającej logowania wygląda tak:

```python
import requests
from bs4 import BeautifulSoup

s = requests.Session()

# Krok 1: pobierz stronę logowania (GET)
# — na realnych stronach tu wyciągamy token CSRF z formularza
r = s.get("http://localhost:5000/login")

# Krok 2: wyślij formularz logowania (POST)
r = s.post("http://localhost:5000/login",
           data={"username": "admin", "password": "secret"})

# Krok 3: pobierz chronione dane (GET) — cookie jest w sesji
r = s.get("http://localhost:5000/dashboard")

# Krok 4: parsuj HTML jak zwykle
soup = BeautifulSoup(r.text, "html.parser")
```

To jest ten sam łańcuch narzędzi, którego używaliśmy na Labach 5–6 (parsowanie HTML), ale z dodatkowym krokiem logowania na początku.

---

## Kontrola dostępu: 401 i 403

Dwa kody statusu HTTP sygnalizują problemy z dostępem:

* **401 Unauthorized** — klient nie jest uwierzytelniony. Serwer mówi: „nie wiem, kim jesteś — zaloguj się". W Flask: `return ..., 401` lub `abort(401)`.
* **403 Forbidden** — klient jest uwierzytelniony, ale **nie ma uprawnień** do tego zasobu. Serwer mówi: „wiem, kim jesteś, ale nie masz dostępu". W Flask: `abort(403)`.

Wzorzec ochrony endpointu we Flask:

```python
from flask import abort

@app.route("/admin")
def admin_panel():
    user = session.get("user")
    if not user:
        abort(401)          # niezalogowany
    if user != "admin":
        abort(403)          # zalogowany, ale nie admin
    return "Panel administracyjny"
```

Z perspektywy scrapingu: odpowiedź `401` oznacza, że potrzebna jest sesja (logowanie). Odpowiedź `403` oznacza, że sesja istnieje, ale konto nie ma wystarczających uprawnień — to sygnał, żeby nie próbować dalej z tym kontem.

---

## Podsumowanie

Na tym wykładzie:

* zobaczyliśmy, dlaczego HTTP potrzebuje dodatkowego mechanizmu „pamięci" — cookies,
* poznaliśmy `Set-Cookie` / `Cookie` jako zwykłe nagłówki HTTP — żadnej magii, tylko para klucz–wartość przesyłana w obie strony,
* zbudowaliśmy sesję we Flask (`flask.session`) — dane na serwerze, identyfikator w podpisanym cookie,
* zobaczyliśmy, jak formularz HTML wysyła POST z `application/x-www-form-urlencoded` — i czym to się różni od JSON API, które znamy z Labu 3,
* nauczyliśmy się `requests.Session` — klient programowy, który automatycznie utrzymuje cookies, jak przeglądarka,
* poznaliśmy kody 401 i 403 jako sygnały kontroli dostępu.

**Co dalej:**

* **Lab 7**: budujemy serwer Flask z logowaniem, sesjami i chronionymi podstronami — testujemy ręcznie (przeglądarka, `curl`) i widzimy cookies w nagłówkach.
* **Lab 8**: piszemy klienta w `requests.Session`, który automatycznie loguje się do serwera z Labu 7 i pobiera chronione dane — to jest scraping strony wymagającej uwierzytelnienia.