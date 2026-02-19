---
title: "Wykład 1: HTTP i klienci HTTP"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

# HTTP: od żądania do danych (HTML, pliki, JSON) {-}

## Cele i zakres

Celem wykładu jest wprowadzenie do komunikacji klient–serwer w oparciu o HTTP jako protokół wymiany żądań i odpowiedzi. Zakres obejmuje strukturę żądania (metoda, URL, nagłówki, body) oraz strukturę odpowiedzi (kod statusu, nagłówki, body). Pokazujemy też, jak te elementy przekładają się na realne interakcje z API, w tym pracę z danymi JSON oraz typowe sytuacje błędów i diagnostyki na poziomie protokołu.

## Internet, WWW i komunikacja sieciowa

Internet jest globalną infrastrukturą umożliwiającą komunikację pomiędzy procesami działającymi na różnych komputerach. Komunikacja ta odbywa się zgodnie z ustalonymi protokołami, z których każdy definiuje sposób wymiany danych, format komunikatów oraz reguły ich interpretacji.

Jedną z najważniejszych usług działających w Internecie jest **World Wide Web (WWW)**. WWW opiera się głównie na protokole HTTP i umożliwia pobieranie zasobów takich jak dokumenty tekstowe, obrazy, pliki czy dane w formatach strukturalnych (JSON, XML).

Z punktu widzenia automatycznego pozyskiwania danych:

- strona WWW,
- endpoint API,
- plik CSV,
- odpowiedź JSON

są tym samym zjawiskiem technicznym: **odpowiedzią HTTP przesyłaną z serwera do klienta**.

## Model klient–serwer i rola HTTP

Komunikacja w WWW odbywa się w modelu **klient–serwer**.

**Klient** to program, który inicjuje połączenie, wysyła żądanie, odbiera odpowiedź i interpretuje otrzymane dane. Przykłady klientów:

- przeglądarka internetowa,
- narzędzie wiersza poleceń (`curl`),
- skrypt w Pythonie (`requests`),
- program automatycznie pobierający dane (crawler, bot).

**Serwer** to program, który nasłuchuje żądań, przetwarza je i generuje odpowiedzi. Kluczowa cecha: **serwer nie inicjuje komunikacji** – zawsze reaguje na żądanie klienta.

**HTTP (Hypertext Transfer Protocol)** jest protokołem warstwy aplikacji, zaprojektowanym jako mechanizm wymiany komunikatów typu *żądanie → odpowiedź*.

### Bezstanowość (i co to oznacza w praktyce)

HTTP jest protokołem **bezstanowym** – każde żądanie jest niezależne. W praktyce „stan” bywa symulowany przez:

- identyfikatory sesji (np. cookies),
- tokeny autoryzacyjne przesyłane w nagłówkach (np. `Authorization`).

Na tym etapie wystarczy rozumieć konsekwencję: jeśli serwer ma wykonać akcję zależną od kontekstu, to **kontekst musi przyjść w żądaniu**.

## Komunikaty HTTP: żądanie i odpowiedź

### URL, zasób, endpoint

- **URL** (np. `https://example.com/search?q=python`) opisuje *gdzie* wysłać żądanie.
- **Zasób** to „co” chcemy pobrać (np. `/index.html`, `/api/patients`).
- **Endpoint API** to zwykle zasób, który zwraca dane (często JSON), np. `/api/v1/items`.

W praktyce będziemy operować na trzech częściach URL:

- **host**: `example.com`
- **ścieżka**: `/search`
- **parametry zapytania** (query string): `q=python`

### Struktura żądania HTTP

Każde żądanie HTTP składa się z:

- linii startowej (metoda, zasób, wersja protokołu),
- nagłówków (pary klucz–wartość),
- ciała (opcjonalnie).

Przykład (HTTP/1.1, zapis tekstowy):

```
GET /index.html HTTP/1.1
Host: example.com
User-Agent: curl/8.0
Accept: */*
```

### Struktura odpowiedzi HTTP

Odpowiedź HTTP składa się z:

- linii statusu,
- nagłówków,
- ciała odpowiedzi.

Przykład:

```
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1256

<html>...</html>
```

### Najważniejsze nagłówki HTTP

Poniżej zestaw minimum, które warto kojarzyć od początku.

**Typowe nagłówki w żądaniu (request):**

| Nagłówek | Po co? | Przykład |
|---|---|---|
| `Host` | wskazuje host (w HTTP/1.1 obowiązkowy) | `Host: example.com` |
| `User-Agent` | identyfikacja klienta | `User-Agent: curl/8.0` |
| `Accept` | jakie formaty akceptuje klient | `Accept: application/json` |
| `Content-Type` | format ciała żądania (gdy wysyłasz dane) | `Content-Type: application/json` |
| `Authorization` | uwierzytelnianie (token) | `Authorization: Bearer …` |

**Typowe nagłówki w odpowiedzi (response):**

| Nagłówek | Po co? | Przykład |
|---|---|---|
| `Content-Type` | format treści | `application/json; charset=utf-8` |
| `Content-Length` | rozmiar odpowiedzi (bajty) | `1256` |
| `Location` | cel przekierowania (3xx) | `Location: /new-path` |
| `Set-Cookie` | ustawienie cookies (stan/sesja) | `Set-Cookie: session=…` |
| `Retry-After` | kiedy próbować ponownie (np. po 429/503) | `Retry-After: 120` |

Warto odróżniać:

- **`Accept`**: *co klient chciałby dostać* (preferencja),
- **`Content-Type`**: *co faktycznie jest wysyłane/otrzymane* (format ciała komunikatu).

Serwer może zignorować `Accept` albo nie być w stanie spełnić preferencji — dlatego finalnie zawsze ufamy `Content-Type` w odpowiedzi.

### Metody HTTP

Najczęściej spotkasz:

- `GET` – pobieranie zasobów (nie powinno zmieniać stanu serwera),
- `POST` – wysyłanie danych do serwera (często tworzenie zasobów lub uruchomienie akcji),
- `HEAD` – jak `GET`, ale bez ciała odpowiedzi (przydatne do sprawdzenia nagłówków i rozmiaru).

### Kody statusu HTTP

Kody statusu informują o wyniku żądania:

- **2xx** – sukces (np. `200 OK`)
- **3xx** – przekierowanie (np. `301`, `302`)
- **4xx** – błąd po stronie klienta (np. `404 Not Found`, `403 Forbidden`, `429 Too Many Requests`)
- **5xx** – błąd serwera (np. `500`, `503`)

W automatycznym pobieraniu danych kod statusu jest sygnałem sterującym: odpowiedź `200` i `404` wymagają zupełnie innego postępowania.

## Klienci HTTP

Zanim przejdziemy do klientów HTTP, warto najpierw wyjaśnić, czym jest URL.

### URL

URL (*Uniform Resource Locator*) to adres zasobu w sieci. W kontekście HTTP najczęściej ma postać:

**`scheme://host[:port]/path?query#fragment`**

Przykład: `https://api.example.org/v1/users/123?verbose=1#section2`

#### Elementy URL {-}

**Schemat (`scheme`)**

Zwykle `http` lub `https`. `https` to HTTP z szyfrowaniem (TLS).

**Host (`host`)**

Domena lub IP, np. `example.com`, `api.example.org`, `192.0.2.10`.

**Port (`:port`)**

Opcjonalny. Domyślnie `80` dla `http` i `443` dla `https`. Jeśli jest inny, pojawia się jawnie, np. `http://localhost:8000/...`.

**Ścieżka (`/path`)**

Identyfikuje zasób lub “trasę” w API, np. `/v1/users/123`.

**Query (`?query`)**

Parametry w formacie `klucz=wartość`, rozdzielane `&`, np. `?page=2&sort=name`.
Typowe zastosowania: filtrowanie, paginacja, sortowanie. (Format odpowiedzi często lepiej negocjować nagłówkiem `Accept` niż parametrem query.)

**Fragment (`#fragment`)**

skazuje miejsce w dokumencie po stronie klienta (np. sekcję w HTML).
Kluczowe: **część `#...` nie jest wysyłana do serwera w żądaniu HTTP**.

#### Kolekcja vs element w ścieżce URL {-}

To rozróżnienie jest konwencją spotykaną w API (zwłaszcza REST). Wynika głównie z **nazewnictwa**, a nie ze specjalnej składni; ostatecznie znaczenie definiuje serwer.

**Kolekcja (zbiór elementów)**

Najczęściej rzeczownik w liczbie mnogiej, np. `/users`, `/orders`.
Typowo: `GET /users` zwraca listę, a `POST /users` tworzy nowy element.

**Element (konkretna instancja zasobu)**

Najczęściej kolekcja + identyfikator, np. `/users/123`.
Typowo: `GET /users/123` zwraca szczegóły, `PUT/PATCH` aktualizuje, `DELETE` usuwa.

**Kolekcje zagnieżdżone**

Np. `/users/123/posts` (kolekcja zależna) i `/users/123/posts/9` (konkretny element).

Uwaga: bez dokumentacji lub odpowiedzi serwera nie da się zawsze pewnie stwierdzić, co autor API miał na myśli (to tylko heurystyka).

#### Kodowanie znaków w URL (percent-encoding) {-}

Nie wszystkie znaki mogą występować w URL wprost (np. spacje, znaki diakrytyczne). Wtedy stosuje się kodowanie procentowe, np. spacja jako `%20`. W praktyce: **nie koduj ręcznie**, tylko korzystaj z narzędzi/bibliotek, które poprawnie kodują parametry.

#### Najczęstsze błędy {-}

* Użycie `?` więcej niż raz:
  - ✅ `/search?q=abc&lang=pl`
  - ❌ `/search?q=abc?lang=pl`
* Mylenie `&` (kolejny parametr) z `#` (fragment po stronie klienta).
* Ręczne sklejanie parametrów bez kodowania znaków (spacje, `&`, `=` wewnątrz wartości).


### curl – klient HTTP w wierszu poleceń

**Charakterystyka.** `curl` to uniwersalne narzędzie do wykonywania żądań HTTP z terminala. Jest świetne do nauki, bo nie ukrywa szczegółów (nagłówków, kodów statusu, przekierowań) i pozwala precyzyjnie kontrolować żądanie.

---

**Najczęściej używane opcje (co robią):**

* `-X <METODA>` – wymusza metodę HTTP (np. `GET`, `POST`, `PUT`, `DELETE`).
  Uwaga: samo `-d/--data` zwykle powoduje użycie `POST` nawet bez `-X`.
* `-H "Nagłówek: wartość"` – dodaje nagłówek do żądania (możesz używać wielokrotnie).
* `-d '...'` / `--data '...'` – wysyła body jako dane formularza (`application/x-www-form-urlencoded`), o ile nie ustawisz innego `Content-Type`.
* `--data-urlencode "k=v"` – jak `--data`, ale z poprawnym URL-encodingiem (bezpieczne dla spacji, znaków specjalnych).
* `-G` – traktuje dane z `--data/--data-urlencode` jako parametry query (czyli robi `GET ?k=v` zamiast body).
* `-i` – wypisuje **nagłówki odpowiedzi + body** (nagłówki na początku).
* `-I` – wysyła `HEAD` i wypisuje **same nagłówki** odpowiedzi (bez body).
* `-v` – tryb diagnostyczny: pokazuje szczegóły połączenia, wysyłane nagłówki itd. (na stderr).
* `-s` – tryb “silent”: wycisza pasek postępu i część komunikatów.
* `-S` – gdy używasz `-s`, to `-S` wymusza wypisanie błędów (sensowne połączenie: `-sS`).
* `-L` – podąża za przekierowaniami (`3xx Location:`).
* `-o <plik>` – zapisuje body do pliku (OS-agnostyczne).
* `-w "<format>"` – dopisuje na końcu własne podsumowanie (np. kod statusu, czas odpowiedzi).
* `--max-time <sek>` – limit czasu całego żądania.
* `--connect-timeout <sek>` – limit czasu na nawiązanie połączenia.
* `--fail` – traktuje odpowiedzi `>=400` jako błąd (przydatne w skryptach).

---

**Podstawowe żądanie GET**

```bash
curl https://example.com
```

**GET z parametrami query (bez ręcznego kodowania znaków)**

```bash
curl -G "https://httpbin.org/get" --data-urlencode "q=ala ma kota" --data-urlencode "page=1"
```

**Wyświetlenie samych nagłówków odpowiedzi**

```bash
curl -I https://example.com
```

**Nagłówki + body (czytelne do szybkiego “co zwróciło API?”)**

```bash
curl -i https://httpbin.org/json
```

**Tryb diagnostyczny (co dokładnie wysyłasz i co serwer odpowiada)**

```bash
curl -v https://example.com
```

**Podążanie za przekierowaniami (np. http → https)**

```bash
curl -L https://example.com
```

---

**Pobieranie JSON i “ładne” formatowanie**

```bash
curl -sS -H "Accept: application/json" https://httpbin.org/json | python -m json.tool
```

* `-H "Accept: application/json"` mówi serwerowi: “preferuję odpowiedź w JSON”.
* `python -m json.tool` formatuje JSON i sprawdza poprawność składni.

---

**Wysyłanie JSON (POST) + kontrola nagłówków**

```bash
curl -sS -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"name":"Ala","score":42}'
```

* `Content-Type` opisuje **format body, które wysyłasz**.
* `Accept` opisuje **format odpowiedzi, którego oczekujesz**.

---

**Status code + zapis odpowiedzi do pliku**

Zapisz body do pliku i wypisz sam kod:

```bash
curl -sS -o response.txt -w "%{http_code}\n" https://example.com
```

* `-o response.txt` zapisuje treść odpowiedzi do pliku (działa na każdym OS).
* `-w "%{http_code}\n"` wypisuje kod statusu na stdout.

Wariant dla API (np. JSON):

```bash
curl -sS -o response.json -w "%{http_code}\n" https://httpbin.org/json
```

`-w/--write-out` przyjmuje **szablon tekstowy**: zwykłe znaki są wypisywane dosłownie, a fragmenty w postaci `%{...}` są **podmieniane** na wartości zmierzone/znane dla danego żądania (kod statusu, czas, rozmiar itd.). To jest bardzo podobne ideowo do **f-stringa** w Pythonie: wstawki “specjalne” są interpolowane w zwykły tekst.

#### `-w` (write-out): “f-string” dla wyników curl {-}

**Składnia:**

* po `-w` podajesz łańcuch, np. `"HTTP=%{http_code} time=%{time_total}s\n"`
* `curl` wypisze ten tekst **po zakończeniu żądania**, zastępując:

  * `%{http_code}` → np. `200`
  * `%{time_total}` → np. `0.123456`

**Przykład 1: tylko kod statusu**

```bash
curl -sS -o response.txt -w "HTTP=%{http_code}\n" https://example.com
```

**Przykład 2: kod + typ treści**

```bash
curl -sS -o response.txt -w "HTTP=%{http_code} CT=%{content_type}\n" https://httpbin.org/json
```

**Przykład 3: kod + czas**

```bash
curl -sS -o response.txt -w "HTTP=%{http_code} time=%{time_total}s\n" https://example.com
```

**Najczęściej używane wstawki `%{...}`:**

* `%{http_code}` – kod statusu HTTP
* `%{content_type}` – `Content-Type` odpowiedzi
* `%{time_total}` – całkowity czas wykonania żądania (sekundy)
* `%{size_download}` – liczba pobranych bajtów
* `%{url_effective}` – finalny URL (po przekierowaniach, jeśli użyto `-L`)


---

**Najczęstsze błędy i jak je szybko zdiagnozować**

* “Nie wiem czemu nie działa” → dodaj `-v` (zobaczysz nagłówki i przekierowania).
* “Skrypt ma działać niezawodnie” → użyj `-sS --fail --max-time 10`.
* “Serwer zwraca HTML zamiast JSON” → dodaj `-H "Accept: application/json"` i sprawdź `Content-Type` w odpowiedzi (`-i` albo `-v`).


### Python: biblioteka requests

**Charakterystyka.** `requests` to wysokopoziomowa biblioteka Pythona do HTTP:

- upraszcza składnię,
- automatycznie obsługuje część szczegółów (np. przekierowania),
- dobrze współpracuje z JSON-em.

**Proste żądanie GET (tekst)**

```python
import requests

r = requests.get("https://example.com")
print(r.status_code)
print(r.text[:200])
```

**Dostęp do nagłówków**

```python
r.headers  # słownik-podobny obiekt
```

**Sprawdzanie kodu statusu**

```python
if r.status_code == 200:
    print("Sukces")
else:
    print("Błąd", r.status_code)
```

**Pobieranie danych binarnych (np. obraz)**

```python
r = requests.get("https://example.com/image.png")
with open("image.png", "wb") as f:
    f.write(r.content)
```

**Parametry zapytania (query string)**

```python
params = {"q": "python", "page": 2}
r = requests.get("https://example.com/search", params=params)
```

**Wysyłanie danych POST (formularz)**

```python
payload = {"name": "Jan", "age": 30}
r = requests.post("https://httpbin.org/post", data=payload)
```

**Wysyłanie JSON**

```python
r = requests.post(
    "https://httpbin.org/post",
    json={"name": "Jan", "age": 30}
)
```

**Odbieranie JSON**

Najprostsza ścieżka:

```python
import requests

r = requests.get("https://httpbin.org/json", timeout=5)
r.raise_for_status()  # zamienia 4xx/5xx na wyjątek

data = r.json()       # parsowanie JSON -> dict/list
print(type(data))
print(data.keys() if isinstance(data, dict) else len(data))
```

Typowy błąd początkujących: serwer zwraca HTML (np. stronę błędu), a kod próbuje to parsować jako JSON. Dwie praktyczne zasady:

- sprawdzaj `r.status_code` (albo używaj `r.raise_for_status()`),
- sprawdzaj `r.headers.get("Content-Type")` przed `r.json()`.

**Obsługa wyjątków (minimalny wzorzec)**

```python
import requests

try:
    r = requests.get("https://example.com", timeout=5)
    r.raise_for_status()
except requests.exceptions.Timeout:
    print("Timeout")
except requests.exceptions.RequestException as e:
    print("Błąd HTTP:", e)
```

### Serwer HTTP jako źródło odpowiedzi

Dotychczas patrzyliśmy na HTTP od strony klienta. Po drugiej stronie jest **serwer HTTP**: program, który **odbiera żądanie**, **interpretuje je** i **zwraca odpowiedź** w standardowej strukturze:

* **linia statusu** (np. `HTTP/1.1 200 OK`)
* **nagłówki**
* **ciało** (opcjonalnie: HTML/JSON/binarne dane)

Z perspektywy protokołu serwer jest “czarną skrzynką”, ale technicznie wykonuje zwykle te kroki:

**1) Parsowanie żądania**

* metoda (`GET/POST/...`), ścieżka (`/path`), parametry query (`?a=1&b=2`)
* nagłówki (np. `Accept`, `Authorization`, `User-Agent`)
* ciało (np. JSON) + typ z `Content-Type`

**2) Routing i logika**

* wybór “handlera” na podstawie metody i ścieżki (np. `GET /users/123`)
* walidacja danych wejściowych (typy, zakresy, brakujące pola)
* autoryzacja/uwierzytelnienie (jeśli dotyczy)

**3) Budowa odpowiedzi**

* dobór **kodu statusu**
* ustawienie **nagłówków**
* serializacja danych (np. do JSON) lub zwrot błędu w ustalonym formacie

#### Co w praktyce “mówi” odpowiedź serwera

Najbardziej informacyjne elementy odpowiedzi (to one sterują zachowaniem klienta):

* **Status code** – podstawowa informacja o wyniku:

  * `2xx` sukces, `3xx` przekierowanie, `4xx` błąd po stronie klienta, `5xx` błąd serwera
* **`Content-Type`** – w jakim formacie jest body (np. `application/json; charset=utf-8`)
* **`Location`** – gdzie przekierować lub gdzie znajduje się utworzony zasób (często przy `201 Created`)
* **`Cache-Control` / `ETag`** – czy i jak można cachować odpowiedź
* **`Retry-After`** – kiedy spróbować ponownie (często przy limitach/rate limit)
* **`WWW-Authenticate`** – informacja o wymaganym uwierzytelnieniu (np. przy `401`)
