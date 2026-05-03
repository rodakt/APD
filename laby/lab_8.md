---
title: "Lab 8: Klient z sesją — `requests.Session`"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* `requests.Session` jako klient HTTP z trwałym cookie jar — jedyna istotna zmiana w stosunku do gołego `requests.get`/`requests.post`,
* przepływ logowania widziany z perspektywy klienta: POST → 302 → GET, automatyczne podążanie za przekierowaniem,
* diagnostyka udanego logowania: `r.url`, `r.history`, `s.cookies.get_dict()`,
* pełny pipeline scrapingu strony chronionej: logowanie → pobranie HTML → parsowanie BeautifulSoup,
* wiele niezależnych sesji w jednym programie — każdy `Session()` to osobny klient,
* walidacja poprawności logowania jako element pipeline'u (nie tylko `r.status_code == 200`).

Narzędzia: Python (`requests`, `beautifulsoup4`), VSCode, serwer Flask z Lab 7 jako cel scrapingu.

---

# Przygotowanie

Środowisko jak na poprzednich labach: VSCode, dwa terminale.

Sprawdź, czy potrzebne pakiety są dostępne:

```bash
pip install flask requests beautifulsoup4
```

::: {.callout-tip}
## Instalacja pakietów w pracowni
Komputery w pracowni mogą resetować pakiety między sesjami. Na początku każdego labu sprawdź, czy potrzebne pakiety są dostępne, i w razie potrzeby zainstaluj je ponownie.
:::

W tym labie pracujemy w nowym folderze `lab8/`, ale **serwerem jest aplikacja z Labu 7** — ta sama, którą zbudowałeś krok po kroku tydzień temu (`/login`, `/logout`, `/dashboard`, `/admin`, `/notes`).

Otwórz **Terminal 1** w folderze `lab7/` i uruchom serwer:

```bash
flask run --debug -p 5000
```

Pozostaw go uruchomionego przez cały lab. **Terminal 2** otwórz w folderze `lab8/` — tam będzie cały kod tego labu.

::: {.callout-note}
## Sprawdzenie startowe
Otwórz w przeglądarce `http://127.0.0.1:5000/login` — powinieneś zobaczyć formularz logowania. Zaloguj się jako `jan` / `haslo123`, sprawdź `/notes`, wyloguj się. Jeśli to działa, serwer jest gotowy.
:::

---

# Wstęp: gdzie jesteśmy

Lab 7 zakończył się pesymistycznie. Plik `bezsesji.py` pokazał, że dwa kolejne wywołania `requests.post`/`requests.get` **nie współdzielą cookies** — każde żądanie startuje z pustym kontekstem. Logowanie jako pojedyncze wywołanie się powiodło, ale zaraz potem `requests.get("/notes")` wracał na `/login`, bo serwer nie widział żadnego cookie sesyjnego.

Tym razem napiszemy klienta, który **pamięta cookies między żądaniami**. Zmiana jest minimalna: z `requests.<metoda>(...)` przechodzimy na `s.<metoda>(...)`, gdzie `s = requests.Session()`. Reszta API jest identyczna — to jest istota całego labu, więc warto to dostrzec na samym początku.

---

# Demonstracja 1: klient, który pamięta cookies

W folderze `lab8/` utwórz plik `zsesja.py`:

```python
import requests

BASE = "http://127.0.0.1:5000"

s = requests.Session()

# 1. Logowanie — POST z danymi formularza.
print("=== Krok 1: logowanie ===")
r1 = s.post(
    f"{BASE}/login",
    data={"username": "jan", "password": "haslo123"},
)
print(f"Status: {r1.status_code}")
print(f"URL końcowy: {r1.url}")
print(f"Cookies w sesji: {s.cookies.get_dict()}")

# 2. Pobranie chronionej strony — w tej samej sesji.
print("\n=== Krok 2: pobranie /notes ===")
r2 = s.get(f"{BASE}/notes")
print(f"Status: {r2.status_code}")
print(f"URL końcowy: {r2.url}")
print(f"Cookie wysłane do serwera: {r2.request.headers.get('Cookie')}")

# 3. Próba wejścia na /admin (jan nie jest adminem).
print("\n=== Krok 3: próba /admin ===")
r3 = s.get(f"{BASE}/admin")
print(f"Status: {r3.status_code}")
```

Uruchom:

```bash
python zsesja.py
```

Spodziewany wynik:

```
=== Krok 1: logowanie ===
Status: 200
URL końcowy: http://127.0.0.1:5000/dashboard
Cookies w sesji: {'session': '.eJyrVi...'}

=== Krok 2: pobranie /notes ===
Status: 200
URL końcowy: http://127.0.0.1:5000/notes
Cookie wysłane do serwera: session=.eJyrVi...

=== Krok 3: próba /admin ===
Status: 403
```

Porównaj to z `bezsesji.py` z Labu 7. Tam Krok 2 lądował na `/login` (przekierowanie wymuszone brakiem sesji), Krok 3 zwracał 401. Tutaj wszystkie trzy żądania widzą tę samą tożsamość: `jan` jest zalogowany, więc `/notes` działa, a `/admin` zwraca 403 — bo `jan` jest uwierzytelniony, ale **nie jest adminem**. To jest dokładnie różnica między 401 a 403, z którą zmierzyliśmy się na Labie 7 — tylko teraz po stronie klienta.

Zwróć uwagę na trzy szczegóły:

* **Krok 1: status 200, URL `/dashboard`.** Wysłaliśmy POST na `/login`, serwer odpowiedział `302 → /dashboard`, a `requests` automatycznie podążył za przekierowaniem (`allow_redirects=True` to wartość domyślna). Ostatecznie `r1` to odpowiedź na GET `/dashboard`, nie na POST `/login`.
* **Krok 2: cookie `session` jest dosłane.** Sesja `s` przechowuje cookie otrzymane w Kroku 1 i automatycznie dokleja je do każdego kolejnego żądania — dokładnie tak, jak robi to przeglądarka.
* **Krok 3: 403, nie 401.** Gdyby `Session` nie pamiętał cookies, dostalibyśmy 401 (jak w `bezsesji.py`). 403 dowodzi, że serwer **rozpoznaje** klienta — ale rola `jan` nie wystarcza.

::: {.callout-note}
## Checkpoint
1. Czy w Kroku 1 `r1.url` kończy się na `/dashboard`?
2. Czy `s.cookies.get_dict()` zawiera klucz `session`?
3. Czy w Kroku 2 nagłówek `Cookie` jest niepusty?
4. Czy Krok 3 zwraca **403** (a nie 401)? Dlaczego ta różnica jest istotna?
:::

::: {.callout-tip}
## `Session` to nie magia
`requests.Session` to obiekt, który przechowuje wewnętrzny *cookie jar* (`s.cookies`) i automatycznie dokleja jego zawartość do każdego żądania wykonanego przez `s.get`/`s.post`. Każda odpowiedź z nagłówkiem `Set-Cookie` aktualizuje ten jar. To wszystko — ten sam mechanizm, który przeglądarka realizuje od strony użytkownika, tu masz w obiekcie Pythona.
:::

---

# Demonstracja 2: anatomia logowania

Demo 1 ukryło istotny szczegół: `r1.status_code` to 200, ale to **nie był** kod odpowiedzi z `/login`. To był kod z `/dashboard`, na który `requests` przekierowało nas automatycznie. Zobaczmy, co dokładnie się stało, i jak rozpoznać sukces logowania.

Utwórz plik `anatomia.py`:

```python
import requests

BASE = "http://127.0.0.1:5000"


def opisz(r: requests.Response) -> None:
    print(f"  Final status: {r.status_code}")
    print(f"  Final URL:    {r.url}")
    print(f"  Historia:     {[(h.status_code, h.url) for h in r.history]}")


# Scenariusz 1: poprawne logowanie.
print("=== Scenariusz 1: jan / haslo123 ===")
s1 = requests.Session()
r = s1.post(f"{BASE}/login", data={"username": "jan", "password": "haslo123"})
opisz(r)
print(f"  Cookies sesji: {s1.cookies.get_dict()}")

# Scenariusz 2: błędne hasło.
print("\n=== Scenariusz 2: jan / ZLEHASLO ===")
s2 = requests.Session()
r = s2.post(f"{BASE}/login", data={"username": "jan", "password": "ZLEHASLO"})
opisz(r)
print(f"  Cookies sesji: {s2.cookies.get_dict()}")

# Scenariusz 3: nieznany login.
print("\n=== Scenariusz 3: nieznany / cokolwiek ===")
s3 = requests.Session()
r = s3.post(f"{BASE}/login", data={"username": "nieznany", "password": "x"})
opisz(r)
print(f"  Cookies sesji: {s3.cookies.get_dict()}")
```

Uruchom. Spodziewany wynik:

```
=== Scenariusz 1: jan / haslo123 ===
  Final status: 200
  Final URL:    http://127.0.0.1:5000/dashboard
  Historia:     [(302, 'http://127.0.0.1:5000/login')]
  Cookies sesji: {'session': '.eJyrVi...'}

=== Scenariusz 2: jan / ZLEHASLO ===
  Final status: 401
  Final URL:    http://127.0.0.1:5000/login
  Historia:     []
  Cookies sesji: {}

=== Scenariusz 3: nieznany / cokolwiek ===
  Final status: 401
  Final URL:    http://127.0.0.1:5000/login
  Historia:     []
  Cookies sesji: {}
```

Zwróć uwagę na trzy sygnały, które razem opisują „udane logowanie":

| Sygnał | Sukces | Porażka |
|---|---|---|
| `r.url` | `…/dashboard` | `…/login` |
| `r.history` | `[<302>]` (jeden element) | `[]` (pusta) |
| `s.cookies.get_dict()` | zawiera `session` | pusty |

Najsilniejszy sygnał to `r.history`. Pusta historia oznacza, że serwer odpowiedział od razu (a ponieważ `/login` przy poprawnym haśle **zawsze** zwraca 302, brak przekierowania = brak sukcesu). Drugim dobrym sygnałem jest końcowy URL — jeśli zostaliśmy na `/login`, znaczy, że formularz wrócił z błędem.

Sam `r.status_code == 200` to **zły** sygnał: w obu scenariuszach 200 może oznaczać „dashboard" albo „strona błędu z formularzem". Status 401 jest informatywny tylko dlatego, że ten konkretny serwer go zwraca — inne serwery mogą zwracać 200 z błędem w ciele HTML.

::: {.callout-note}
## Checkpoint
1. Czy w Scenariuszu 1 `r.history` zawiera dokładnie jeden element ze statusem 302?
2. Czy w Scenariuszach 2 i 3 `s.cookies` jest pusty?
3. Dlaczego `r.status_code == 200` nie wystarcza do rozpoznania udanego logowania?
:::

::: {.callout-tip}
## `r.history` w `requests`
`r.history` to lista odpowiedzi pośrednich, przez które klient przeszedł, zanim zatrzymał się na finalnej. Przy logowaniu PRG mamy zawsze dokładnie jeden element: 302 z `/login`. Przy zwykłym GET strony bez przekierowań lista jest pusta. Jeśli chcesz wyłączyć podążanie za przekierowaniami (jak w Labie 7 dla diagnostyki), użyj `allow_redirects=False`.
:::

---

# Ćwiczenie 1: pełny pipeline scrapingu strony chronionej

Czas zamknąć łańcuch narzędzi, który budujemy od pierwszego labu:

```
POST /login (Session)  →  GET /notes (Session)  →  BeautifulSoup  →  lista notatek
```

Każde z tych ogniw widziałeś już osobno: `requests.post` (Lab 1), serwer z formularzem (Lab 7), `BeautifulSoup` (Lab 5). Teraz złożymy je w jeden program.

## Zadanie

Utwórz plik `notatki_jana.py`:

```python
import requests
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:5000"

s = requests.Session()

# 1. Zaloguj się jako jan.
# --- Twój kod ---

# 2. Pobierz stronę /notes.
# --- Twój kod ---

# 3. Sparsuj HTML i wyciągnij teksty wszystkich <li> z listy notatek.
#    Wskazówka: notatki są w pojedynczym <ul>, każda jako <li>.
# --- Twój kod ---

# 4. Wypisz każdą notatkę w osobnej linii, z numeracją.
# --- Twój kod ---
```

Uruchom:

```bash
python notatki_jana.py
```

## Spodziewany wynik

```
1. Kupić mleko
2. Zadzwonić do mamy
3. Oddać książkę do biblioteki
```

::: {.callout-note}
## Checkpoint
1. Czy widzisz dokładnie trzy notatki Jana w wyniku?
2. Co się stanie, jeśli zakomentujesz logowanie (krok 1) i uruchomisz tylko kroki 2–4? Spróbuj — co znajdziesz w `r.text`? (Wskazówka: będzie to formularz logowania, bo `/notes` przekierowuje niezalogowanego klienta na `/login`.)
3. Co się stanie, jeśli w `s.post(...)` użyjesz `json={...}` zamiast `data={...}`? Spróbuj — dlaczego logowanie się nie powiedzie? (Powrót do Wykładu 4: formularz HTML wysyła `application/x-www-form-urlencoded`, nie JSON.)
:::

::: {.callout-tip}
## Selektor `ul li`
W szablonie strony `/notes` jest dokładnie jeden `<ul>` z notatkami. Selektor CSS `ul li` znajdzie wszystkie `<li>` wewnątrz dowolnego `<ul>` na stronie — w naszym przypadku to ta jedna lista. Pełny selektor mógłby być bardziej szczegółowy, ale dla tej strony `ul li` wystarcza.
:::

---

# Ćwiczenie 2: trzy konta, trzy sesje

Sesja w `requests` to nie tylko cookie jar. To **tożsamość klienta** — każdy `Session()` zachowuje się jak osobna przeglądarka, z osobnym kompletem zalogowanych użytkowników. W tym ćwiczeniu zescrapujesz notatki **wszystkich trzech** użytkowników, każdego w osobnej sesji.

## Zadanie

Utwórz plik `wszystkie_notatki.py`:

```python
import time
import requests
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:5000"

UZYTKOWNICY = [
    ("admin", "secret"),
    ("jan", "haslo123"),
    ("anna", "qwerty"),
]


def pobierz_notatki(login: str, haslo: str) -> list[str]:
    """Loguje użytkownika w nowej sesji i zwraca listę jego notatek."""
    # 1. Utwórz nową sesję dla tego użytkownika.
    # --- Twój kod ---

    # 2. Zaloguj się.
    # --- Twój kod ---

    # 3. Pobierz /notes.
    # --- Twój kod ---

    # 4. Sparsuj listę notatek i zwróć ją.
    # --- Twój kod ---


# Pętla po użytkownikach z agregacją wyników.
wszystkie = {}
for login, haslo in UZYTKOWNICY:
    wszystkie[login] = pobierz_notatki(login, haslo)
    time.sleep(0.1)  # etyka — także wobec localhost

# Wypisz zebrany materiał.
for login, notatki in wszystkie.items():
    print(f"\n=== {login} ({len(notatki)}) ===")
    for n in notatki:
        print(f"  - {n}")
```

## Spodziewany wynik

```
=== admin (2) ===
  - TODO: zrobić backup bazy
  - Spotkanie z zespołem w piątek

=== jan (3) ===
  - Kupić mleko
  - Zadzwonić do mamy
  - Oddać książkę do biblioteki

=== anna (1) ===
  - Brak notatek.
```

::: {.callout-warning}
## Anna i „Brak notatek."
Anna ma jedną „notatkę" o treści `Brak notatek.` — i to nie jest błąd Twojego kodu. To **placeholder**, który serwer wkleja do `<li>`, gdy lista użytkownika jest pusta (zajrzyj do `lab7/app.py`, do funkcji `notes`). Z perspektywy parsera HTML jest to dokładnie taki sam `<li>` jak realna notatka — selektor `ul li` go znajdzie i zwróci.

To jest typowa pułapka scrapingu: **HTML to nie surowe dane**. To, co widzimy oczami jako „pustą listę", w drzewie DOM jest jednoelementową listą z komunikatem. Aplikacje frontendowe rzadko sygnalizują pustkę przez brak elementów — częściej wstawiają widget zastępczy.

Jak to naprawić? W tym labie zostawiamy wynik jak jest — uświadomienie problemu jest celem. W realnym scraperze: albo dopasowałbyś selektor, żeby pominąć placeholder (np. używając atrybutu lub klasy CSS, jeśli jest), albo dodałbyś warunek pomijający `li` zawierające tag `<i>`.
:::

::: {.callout-note}
## Checkpoint
1. Czy `admin` widzi tylko swoje notatki, a `jan` tylko swoje?
2. Co się stanie, jeśli **przeniesiesz** linię `s = requests.Session()` z funkcji `pobierz_notatki` na sam początek pliku (poza pętlę), tak by wszyscy użytkownicy używali tej samej sesji? Spróbuj — czyje notatki dostanie każda iteracja? (Wskazówka: każdy nowy POST `/login` nadpisuje sesję poprzednika, ale… spójrz, czyje notatki widzi `anna` w drugim przebiegu — i pomyśl, dlaczego.)
3. Dlaczego `time.sleep(0.1)` znajduje się **w pętli żądań**, a nie tylko po pętli? (Powtórka z Labu 4: każde żądanie do dowolnego serwera — także lokalnego — robimy z odstępem; to staje się odruchem, niezależnie od adresata.)
:::

---

# Ćwiczenie 3: walidacja logowania

Pliki z Ćwiczeń 1 i 2 zakładają, że logowanie zawsze się powiedzie. W praktyce nigdy tak nie jest: hasło może być błędne, użytkownik zablokowany, formularz zmieniony. Każdy poważny pipeline musi **sprawdzać**, czy logowanie się udało, i czytelnie reagować, gdy nie.

W Demonstracji 2 widziałeś trzy sygnały sukcesu. Teraz zamkniesz je w funkcję, która zwraca proste `True`/`False`.

## Zadanie

Utwórz plik `walidacja.py`:

```python
import requests

BASE = "http://127.0.0.1:5000"


def zaloguj(s: requests.Session, login: str, haslo: str) -> bool:
    """Próbuje zalogować się w sesji `s`. Zwraca True przy sukcesie, False przy porażce.

    Funkcja nie rzuca wyjątku przy błędnym haśle — porażka logowania to
    normalny przypadek, nie błąd programu.
    """
    # 1. Wyślij POST na /login z danymi formularza.
    # --- Twój kod ---

    # 2. Zwróć True, jeśli serwer przekierował nas na /dashboard,
    #    False w przeciwnym razie.
    # --- Twój kod ---


# Testy — każdy w nowej sesji, żeby wyniki się nie nakładały.
przypadki = [
    ("jan", "haslo123"),       # poprawne
    ("jan", "ZLEHASLO"),       # poprawny login, błędne hasło
    ("nieznany", "byle_co"),   # login nie istnieje
    ("admin", "secret"),       # poprawne, inny user
    ("", ""),                  # puste pola
]

for login, haslo in przypadki:
    s = requests.Session()
    ok = zaloguj(s, login, haslo)
    znacznik = "OK " if ok else "FAIL"
    print(f"[{znacznik}] {login!r} / {haslo!r}")
```

## Spodziewany wynik

```
[OK ] 'jan' / 'haslo123'
[FAIL] 'jan' / 'ZLEHASLO'
[FAIL] 'nieznany' / 'byle_co'
[OK ] 'admin' / 'secret'
[FAIL] '' / ''
```

::: {.callout-note}
## Checkpoint
1. Czy wszystkie cztery przypadki failowe zwracają `False`?
2. Jaki konkretnie sygnał sukcesu wybrałeś — `r.url`, `r.history`, czy zawartość `s.cookies`? Czy potrafisz uzasadnić wybór?
3. Co by się stało, gdybyś **dwukrotnie** wywołał `zaloguj(s, "jan", "ZLEHASLO")` na **tej samej** sesji `s`, która wcześniej zalogowała `jana` poprawnie? Spróbuj — czy `s` traci zalogowanie po nieudanej próbie?
:::

::: {.callout-tip}
## Walidacja jako kontrakt funkcji
`zaloguj` zwraca `bool`, nie rzuca wyjątku. To celowe: nieudane logowanie nie jest awarią programu, tylko jednym z dwóch normalnych wyników. Wyjątki rezerwujemy dla rzeczy nieoczekiwanych — np. brak połączenia z serwerem (`requests.exceptions.ConnectionError`). Ten kontrakt — `bool` dla rezultatów dziedzinowych, wyjątki dla błędów technicznych — przyda się też przy klientach Scrapy i async.
:::

---

# Co dalej w realu: token CSRF

::: {.callout-warning}
## Realne formularze logowania chroni token CSRF
Serwer z Labu 7 jest celowo uproszczony — nie ma zabezpieczenia CSRF. W realnych aplikacjach formularz logowania zawiera dodatkowe ukryte pole, np.:

```html
<input type="hidden" name="csrf_token" value="a1b2c3d4...">
```

Wartość tokenu jest losowa i ważna tylko dla danej sesji. Serwer odrzuca POST bez tokenu lub z nieprawidłowym tokenem (zwykle kodem 400 lub 403). Dla scrapera oznacza to **dwa żądania** zamiast jednego:

1. **GET `/login`** — pobierz stronę z formularzem, wyciągnij `csrf_token` przez BeautifulSoup,
2. **POST `/login`** — wyślij dane formularza razem z odzyskanym tokenem.

`requests.Session` jest tu dodatkowo niezbędna: token CSRF często idzie w parze z tymczasowym cookie sesyjnym ustawianym już przy GET — bez sesji para token-cookie nie pasuje do siebie po stronie serwera.

W tym labie ten krok pomijamy, ale wzorzec jest dokładnie taki sam jak Ćwiczenie 1, tylko z dodatkowym GET-em na początku. Wrócimy do tego konceptualnie w Labie 13 (Selenium), gdzie przeglądarka załatwia tę logikę za nas.
:::

---

# Podsumowanie

W tym labie:

* zobaczyłeś, że jedyną istotną różnicą między „klientem niedziałającym" (Lab 7, `bezsesji.py`) a „klientem działającym" jest jeden obiekt — `requests.Session()`,
* zdiagnozowałeś przepływ logowania PRG po stronie klienta: `r.history`, `r.url`, `s.cookies` jako trzy uzupełniające się sygnały,
* zamknąłeś pełny pipeline scrapingu chronionej strony: logowanie → pobranie HTML → parsowanie BS4 → dane,
* zescrapowałeś dane trzech niezależnych użytkowników w trzech sesjach — każda jak osobny klient,
* zauważyłeś, że HTML rendowany dla pustej listy też zwraca element listy (placeholder) — pułapka, którą trzeba widzieć,
* wyodrębniłeś walidację logowania jako funkcję zwracającą `bool`, gotową do wpięcia w większy program.

**Co dalej:**

* **Wykład 5**: asynchroniczność. Mamy działającego klienta, który potrafi się zalogować — ale jest **wolny**. Scraping notatek trzech użytkowników to sześć sekwencyjnych żądań HTTP. Co, gdyby trzeba było tysiąca? Odpowiedzią jest `httpx.AsyncClient` i `asyncio`.
* **Lab 9**: pierwszy lab asynchroniczny — `asyncio` od podstaw, prowadzone ćwiczenia.
* **Lab 10**: async HTTP w praktyce — porównanie sync vs async, `Semaphore`, `gather`, `as_completed`.
