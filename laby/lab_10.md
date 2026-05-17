---
title: "Lab 10: Async HTTP w praktyce"
subtitle: "Automatyczne pozyskiwanie danych - ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

W Lab 9 zobaczyłeś, że async daje ~10× przyspieszenie na dziesięciu żądaniach. Dziś sprawdzimy, co się dzieje, gdy żądań jest sto, niektóre się sypią, a niektóre wiszą. Innymi słowy: przechodzimy z „działa" do „działa w praktyce".

Zakres materiału:

* skala bez kontroli - co dzieje się przy naiwnym `gather` na ~100 żądaniach,
* `asyncio.Semaphore` jako standardowy ogranicznik współbieżności po stronie klienta,
* limit po stronie serwera - czego klient nie kontroluje,
* dwie strategie obsługi błędów w `gather`: `return_exceptions=True` vs `try/except` w korutynie,
* timeouty w `httpx` - dlaczego są nieodzowne w pracy z `Semaphore`,
* `as_completed` - przetwarzanie wyników w miarę spływania, z raportowaniem postępu,
* pełen pipeline: pobranie wielu żądań z kontrolą współbieżności, timeoutem, obsługą błędów, zapisem sukcesów i porażek do osobnych plików oraz końcowym raportem.

Narzędzia: Python (`asyncio`, `httpx`, Flask), VSCode.

---

# Przygotowanie

Środowisko jak w Lab 9: VSCode, dwa terminale.

Utwórz folder `lab10/` i otwórz go w VSCode. **Terminal 1** uruchomimy z serwerem Flask, **Terminal 2** posłuży do uruchamiania klientów.

Sprawdź, czy potrzebne pakiety są dostępne:

```bash
pip install flask httpx
```

::: {.callout-tip}
## Pakiety
Jeśli pracownia resetuje pakiety między sesjami, zainstaluj ponownie. Nic nowego w stosunku do Lab 9 - `httpx` już znasz.
:::

Skopiuj `app.py` z folderu `lab9/` do `lab10/`. Za chwilę go rozszerzymy.

Każdy krok labu trafia do osobnego pliku (`demo1.py`, `cw1.py`, `cw5.py` itd.). Konwencja ta sama co w Lab 9.

---

# Wstęp: gdzie jesteśmy

Lab 9 zakończył się przyspieszeniem: 10 żądań do `/data/<page>` zsynchronizowanych w pętli zajmuje ~10 s; te same 10 przez `asyncio.gather` i `httpx.AsyncClient` zajmuje ~1 s. Wszystkie `START` w pierwszych milisekundach, wszystkie `DONE` w drugiej sekundzie - czysta wizualna sygnatura współbieżności.

Pytanie, które się natychmiast nasuwa: **a co przy 100? przy 1000?** A co, jeśli serwer czasem rzuca błąd 500? A co, gdy jedno z żądań w ogóle nie odpowiada?

Naiwnie można odpowiedzieć: skoro 10 zajęło 1 s, to 100 zajmie 1 s, a 1000 zajmie 1 s. **W warunkach laboratoryjnych** - na lokalnym serwerze Flask, po loopbacku - to nawet okaże się prawdą. Ale wystarczy podmienić serwer na realny (cudzy, gdzieś w internecie), a okazuje się, że:

* serwer odrzuca część żądań kodem 429 albo 503,
* niektóre żądania wracają po sekundzie, inne po dwudziestu,
* niektóre nie wracają w ogóle,
* twój IP zostaje na chwilę zablokowany.

Asynchroniczność dała nam moc, której **w realnym świecie nie wolno użyć w pełni**. Trzeba ją świadomie ograniczyć. Tym właśnie się dziś zajmujemy.

Pierwsze pół labu spędzimy na motywie „kontrola współbieżności" (Demonstracje 1-2, Ćwiczenie 1). Drugie pół - na motywie „odporność" (Demonstracja 3, Ćwiczenia 2-4). Na koniec składamy wszystko w pełen pipeline (Ćwiczenie 5).

---

# Rozbudowa serwera

Dorzucamy do `app.py` trzy nowe endpointy. Każdy izoluje jedno zjawisko, które będziemy badać.

Otwórz `lab10/app.py` (skopiowany z Lab 9) i zastąp jego zawartość poniższym kodem:

```python
# app.py - serwer dla Lab 10
import random
import threading
import time

from flask import Flask, jsonify

app = Flask(__name__)

# Limit jednoczesnych żądań po stronie serwera - tylko dla /limited.
SERVER_SEM = threading.Semaphore(8)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/data/<int:page>")
def data(page):
    """Endpoint z Lab 9: 1 s opóźnienia, bez żadnych limitów."""
    time.sleep(1)
    return jsonify({
        "page": page,
        "items": [f"item-{page}-{i}" for i in range(5)],
    })


@app.route("/limited/<int:page>")
def limited(page):
    """Jak /data, ale serwer dopuszcza najwyżej 8 jednoczesnych żądań.
    Pozostałe czekają w kolejce na zwolnienie miejsca."""
    with SERVER_SEM:
        time.sleep(1)
    return jsonify({
        "page": page,
        "items": [f"item-{page}-{i}" for i in range(5)],
    })


@app.route("/flaky/<int:page>")
def flaky(page):
    """Jak /data, ale ~30% szans, że zwróci 500."""
    time.sleep(1)
    if random.random() < 0.3:
        return jsonify({"error": "internal server error"}), 500
    return jsonify({
        "page": page,
        "items": [f"item-{page}-{i}" for i in range(5)],
    })


@app.route("/slow/<int:page>")
def slow(page):
    """Opóźnienie losowe od 0.5 do 4.0 s - symuluje serwer o nieprzewidywalnej latencji."""
    delay = random.uniform(0.5, 4.0)
    time.sleep(delay)
    return jsonify({
        "page": page,
        "delay": round(delay, 2),
        "items": [f"item-{page}-{i}" for i in range(5)],
    })
```

Uruchom serwer w **Terminalu 1** (otwartym w `lab10/`):

```bash
flask run --debug -p 5000
```

Pozostaw uruchomionego do końca labu.

::: {.callout-note}
## Sanity check
W **Terminalu 2** sprawdź każdy z nowych endpointów:

```bash
curl http://127.0.0.1:5000/limited/0
curl http://127.0.0.1:5000/flaky/0
curl http://127.0.0.1:5000/slow/0
```

Pierwsze powinno wrócić po sekundzie. Drugie - czasem po sekundzie z JSON-em, czasem po sekundzie z błędem 500 (powtórz parę razy, żeby zobaczyć oba). Trzecie - po przypadkowym czasie między 0.5 a 4 s, z polem `delay` w odpowiedzi.
:::

::: {.callout-tip}
## Cztery endpointy, cztery zjawiska
* **`/data/<page>`** - deterministyczny, bez limitów. Do demonstracji „czysta skala".
* **`/limited/<page>`** - deterministyczny, z limitem po stronie serwera. Do ćwiczeń z `Semaphore`.
* **`/flaky/<page>`** - probabilistyczne błędy. Do ćwiczeń z `try/except` i `return_exceptions`.
* **`/slow/<page>`** - probabilistyczne opóźnienia. Do ćwiczeń z timeoutami i `as_completed`.

Każdy endpoint odpowiada za jedno zjawisko. Ćw 5 połączy je w pełen pipeline.
:::

---

# Demonstracja 1: skalowanie w naiwnej współbieżności

Sprawdźmy, co Lab 9 obiecywał: jeśli 10 żądań współbieżnie trwa 1 s, to 100 też powinno trwać ~1 s.

Utwórz plik `demo1.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 100
START = None


async def fetch_page(client, page):
    r = await client.get(f"{BASE}/data/{page}")
    r.raise_for_status()
    return r.json()


async def main():
    async with httpx.AsyncClient() as client:
        coros = [fetch_page(client, p) for p in range(N)]
        return await asyncio.gather(*coros)


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START
print(f"Pobrano {len(wyniki)} stron w {elapsed:.2f}s")
```

Uruchom. Spodziewany wynik:

```
Pobrano 100 stron w 1.18s
```

Sto żądań. Jedna sekunda z drobnym ogonem. Stukrotne przyspieszenie względem wersji sekwencyjnej (która zajęłaby 100 s).

I tu pada pierwsze pytanie: **czy to jest w porządku?**

Po stronie naszej maszyny - tak. `httpx.AsyncClient` ma domyślny limit puli połączeń na 100 (parametr `max_connections`), więc fizycznie wysyła do 100 jednoczesnych żądań i nie więcej. Pamięci wystarczy, gniazd TCP wystarczy.

Po stronie serwera - **w naszym laboratorium tak**, bo `flask run` obsługuje żądania wielowątkowo, a `time.sleep(1)` blokuje tylko jeden wątek. Sto wątków śpi sobie równolegle, każdy w swoim świecie.

Po stronie realnego serwera, do którego mielibyśmy podpiąć ten sam kod - **niemal nigdy**:

* serwer ma własną pulę połączeń. Sto jednoczesnych żądań od jednego klienta to zachowanie podejrzanie podobne do ataku.
* serwer ma rate limiting. Po przekroczeniu progu odpowiada `429 Too Many Requests` albo wprost blokuje IP.
* nawet bez aktywnej obrony, sto jednoczesnych zapytań do bazy danych zwykle prowadzi do przeciążenia.

Naiwne `gather` na dużym zakresie jest **technicznie poprawne, ale w realiach scrapingu bywa nieakceptowalne**. Trzeba je świadomie ograniczyć.

::: {.callout-note}
## Checkpoint
1. Czy `Pobrano 100 stron w ...s` zwraca czas bliski 1 s? Jeśli wyraźnie powyżej 2 s - sprawdź, czy w `app.py` w endpoincie `/data` jest dokładnie `time.sleep(1)` bez dodatkowej logiki.
2. Zmień `N = 200`. Ile teraz trwa? (Powinno wzrosnąć - `httpx` domyślnie zezwala na 100 jednoczesnych połączeń, więc reszta czeka w kolejce klienta. 200 żądań w dwóch falach po 100 = ~2 s.)
3. Zmień `N = 100` z powrotem i przemyśl: gdyby zamiast `http://127.0.0.1:5000` po drugiej stronie był ogólnodostępny serwis - czy taki kod jest w porządku?
:::

---

# Demonstracja 2: kontrola przez `Semaphore`

Wprowadzamy ogranicznik. Standardowym narzędziem w `asyncio` jest `Semaphore` - licznik, który dopuszcza najwyżej N korutyn do chronionej sekcji jednocześnie. Pozostałe czekają na zwolnienie miejsca.

Utwórz plik `demo2.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 100
LIMIT = 10
START = None


async def fetch_page(client, page, sem):
    async with sem:
        r = await client.get(f"{BASE}/data/{page}")
        r.raise_for_status()
        return r.json()


async def main():
    sem = asyncio.Semaphore(LIMIT)
    async with httpx.AsyncClient() as client:
        coros = [fetch_page(client, p, sem) for p in range(N)]
        return await asyncio.gather(*coros)


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START
print(f"Pobrano {len(wyniki)} stron w {elapsed:.2f}s (limit={LIMIT})")
```

Uruchom. Spodziewany wynik:

```
Pobrano 100 stron w 10.12s (limit=10)
```

**Dziesięć sekund.** Dziesięciokrotnie wolniej niż Demonstracja 1.

To jest celowa zamiana: wymieniamy część przepustowości szczytowej na **kontrolę i przewidywalność**. Klient w dowolnym momencie ma maksymalnie 10 otwartych żądań. 100 żądań idzie w 10 paczkach po 10. Każda paczka trwa ~1 s. Razem ~10 s.

Trzy linijki, które wprowadzają cały mechanizm:

* `sem = asyncio.Semaphore(LIMIT)` - tworzymy licznik na N miejsc.
* `async with sem:` wewnątrz korutyny - czekamy na wolne miejsce, zajmujemy je na czas bloku, zwalniamy po wyjściu z bloku.
* Przekazywanie `sem` do korutyny jako argument - bo Semaphore musi być **jednym wspólnym obiektem** dla wszystkich korutyn, które się nim ograniczają.

::: {.callout-warning}
## Jeden Semaphore na wszystkich
Często spotykany błąd: utworzenie `Semaphore` wewnątrz korutyny zamiast w `main()`.

```python
async def fetch_page_zly(client, page):
    sem = asyncio.Semaphore(10)   # <-- nowy semafor co wywołanie!
    async with sem:
        ...
```

Każda korutyna dostaje swój własny semafor z 10 miejscami. Czyli każda przepuszcza siebie samą bez czekania. Efekt: jak bez semafora w ogóle - 100 jednoczesnych żądań. Reguła: `Semaphore` tworzymy **raz**, w `main` (albo wyżej), i przekazujemy do wszystkich korutyn.
:::

::: {.callout-tip}
## Argument grzeczności
Demonstracja 1 była szybsza w mierzonym sensie. Demonstracja 2 jest poprawniejsza w sensie zasad współżycia z cudzymi serwerami. To wymiana, której **trzeba dokonać świadomie** - i `Semaphore` jest narzędziem, które tę świadomość wyraża w kodzie.

W praktyce: dla każdej domeny, do której masz wysyłać dużo żądań, zacznij od `Semaphore(5)` lub `Semaphore(10)`. Zwiększaj tylko wtedy, gdy masz dowody, że serwer wytrzyma więcej.
:::

::: {.callout-note}
## Checkpoint
1. Czy uzyskany czas to ~10 s, a nie ~1 s? Jeśli ~1 s - sprawdź, czy `sem` jest tworzony w `main()` (nie wewnątrz `fetch_page`).
2. Zmień `LIMIT = 25`. Spodziewaj się ~4 s. (Cztery paczki po 25 = 4 s.)
3. Zmień `LIMIT = 1`. Spodziewaj się ~100 s. (Sto paczek po 1 = klient sekwencyjny.) Możesz to przerwać Ctrl-C, kiedy zrozumiesz, dokąd zmierza.
:::

---

# Ćwiczenie 1: kiedy więcej nie znaczy szybciej

Demonstracje 1 i 2 pokazały, że im wyższy `LIMIT`, tym szybciej. Naturalne pytanie: to po co w ogóle ograniczać, skoro `LIMIT=100` jest najszybszy?

Cała odpowiedź dotąd brzmiała: „grzeczność wobec serwera, etyka, rate limiting". Ale jest jeszcze drugie pół odpowiedzi, mocniejsze i bardziej praktyczne: **klient nie kontroluje całego systemu**. Po drugiej stronie istnieje limit, którego twój `Semaphore(N)` po stronie klienta **nie pokona** - może tylko z nim współpracować.

W naszym laboratorium ten limit jest jawny: w `app.py` widzisz `SERVER_SEM = threading.Semaphore(8)`. Endpoint `/limited/<page>` dopuszcza **najwyżej 8 jednoczesnych żądań**, reszta czeka w kolejce. To jest model tego, co w realu nazywa się rate limiting, connection pool albo „licencja API w wersji free".

W tym ćwiczeniu zmierzymy, jak klient z różnymi `LIMIT` zachowuje się wobec serwera z `SERVER_SEM(8)`.

## Krok A: szkielet skryptu

Utwórz plik `cw1.py`:

```python
import asyncio
import sys
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 40
START = None


async def fetch_page(client, page, sem):
    # 1. Wewnątrz async with sem: wykonaj GET na /limited/<page>,
    #    sprawdź status, zwróć r.json().
    # --- Twój kod ---
    ...


async def main(limit):
    sem = asyncio.Semaphore(limit)
    async with httpx.AsyncClient() as client:
        # 2. Stwórz listę N korutyn fetch_page dla zakresu range(N).
        # 3. Uruchom je przez asyncio.gather i zwróć listę wyników.
        # --- Twój kod ---
        ...


if __name__ == "__main__":
    limit = int(sys.argv[1])  # LIMIT przekazany z linii poleceń
    START = time.perf_counter()
    wyniki = asyncio.run(main(limit))
    elapsed = time.perf_counter() - START
    print(f"limit={limit:3d}  N={N}  czas={elapsed:5.2f}s")
```

Uzupełnij szkielet. Wzorzec jest identyczny jak w Demonstracji 2 - jedyna różnica to endpoint (`/limited` zamiast `/data`) i `limit` przekazany z linii poleceń.

## Krok B: pomiar przy różnych N

Uruchom skrypt z różnymi limitami:

```bash
python cw1.py 2
python cw1.py 4
python cw1.py 8
python cw1.py 16
python cw1.py 40
```

Wypełnij poniższą tabelkę uzyskanymi czasami:

| `limit` po stronie klienta | spodziewany czas | twój czas |
|---:|:---:|:---:|
| 2 | ~20 s | ... |
| 4 | ~10 s | ... |
| 8 | ~5 s | ... |
| 16 | ~5 s | ... |
| 40 | ~5 s | ... |

## Krok C: wniosek

Spodziewany kształt krzywej:

* od `limit=1` do `limit=8` czas **maleje** odwrotnie proporcjonalnie - każda dodatkowa współbieżność po stronie klienta przekłada się na proporcjonalne przyspieszenie.
* od `limit=8` wzwyż czas **przestaje maleć** - utyka w okolicach 5 s i tam zostaje, niezależnie od tego, czy klient próbuje 16, 40 czy 100 jednoczesnych żądań.

Liczba 8 nie jest tu przypadkiem. Tyle pozwala `SERVER_SEM` po stronie serwera. Dla `limit ≤ 8` to klient jest „wąskim gardłem" - serwer ma miejsce dla wszystkich, czekanie wynika z tego, że klient nie wysyła więcej. Dla `limit > 8` to **serwer** jest wąskim gardłem - klient wysyła 16 żądań, serwer przyjmuje 8, pozostałe 8 czeka w kolejce serwerowej i klient nic z tym nie zrobi.

::: {.callout-warning}
## Twój `Semaphore` to twoja decyzja, nie cudzy limit
`Semaphore(16)` w kliencie nie sprawia, że serwer obsłuży 16 jednoczesnych żądań. Sprawia tylko, że klient **wysyła** 16. Decyzja, ile faktycznie obsłużyć, należy do serwera - i bywa wyrażana subtelnie: opóźnieniem, kodem 429, blokadą.

W praktyce: dobieraj `Semaphore` **niżej** niż twoje podejrzenia o pojemność serwera, nie wyżej. Marża bezpieczeństwa kosztuje sekundy; jej brak kosztuje blokadę IP.
:::

::: {.callout-note}
## Checkpoint
1. Czy twoja tabelka pokazuje kolano w okolicach `limit=8`? Jeśli kolano jest gdzie indziej - sprawdź, czy w `app.py` rzeczywiście jest `SERVER_SEM = threading.Semaphore(8)`.
2. Dlaczego `limit=2` i `limit=4` dają liniowe przyspieszenie, a `limit=16` i `limit=40` daje to samo co `limit=8`? Sformułuj odpowiedź własnymi słowami, używając słów „klient", „serwer", „kolejka".
3. W realnym scrapingu nie widzisz `SERVER_SEM` w kodzie cudzego serwera. Jak praktycznie wyznaczyć dobry `limit`? (Wskazówka: zacznij od małej liczby i zwiększaj, dopóki czas maleje - moment, w którym przestaje maleć, jest twoim szczytem.)
:::

---

# Demonstracja 3: jeden błąd zatapia `gather`

Do tej pory wszystkie żądania kończyły się sukcesem. Co się dzieje, gdy choć jedno rzuci błąd?

Utwórz plik `demo3.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 20
START = None


async def fetch_page(client, page):
    r = await client.get(f"{BASE}/flaky/{page}")
    r.raise_for_status()
    return r.json()


async def main():
    async with httpx.AsyncClient() as client:
        coros = [fetch_page(client, p) for p in range(N)]
        return await asyncio.gather(*coros)


START = time.perf_counter()
try:
    wyniki = asyncio.run(main())
    print(f"Pobrano {len(wyniki)} stron")
except httpx.HTTPStatusError as e:
    elapsed = time.perf_counter() - START
    print(f"Po {elapsed:.2f}s wpadł wyjątek: {e}")
    print("Nie wiemy, ile żądań się udało, ani co dostały.")
```

Endpoint `/flaky/<page>` ma 30% szans, że zwróci 500. Przy 20 żądaniach prawdopodobieństwo, że **wszystkie** się udadzą, wynosi $0.7^{20} \approx 0.08\%$. Praktycznie zawsze co najmniej jedno padnie.

Uruchom. Spodziewany wynik (jeden z dwóch):

```
Po 1.04s wpadł wyjątek: Server error '500 INTERNAL SERVER ERROR' for url '...'
Nie wiemy, ile żądań się udało, ani co dostały.
```

Albo (rzadziej, gdyby wszystkie się udały):

```
Pobrano 20 stron
```

Dwa zachowania `gather` warto tu nazwać:

* **`gather` domyślnie propaguje wyjątek** z pierwszej korutyny, która go rzuci. Propaguje go w górę, do kodu wywołującego.
* **Pozostałe korutyny się wtedy gubią**. `gather` nie czeka na ich zakończenie. Wartości, które te korutyny zwróciły, **nigdzie nie trafiają** - są nieosiągalne. Z naszego punktu widzenia: 19 żądań mogło się udać, ale nie mamy do nich dostępu.

W praktyce scrapingu jest to **bezużyteczne zachowanie**. Pobieramy 20 stron z jakiejś listy - jeśli jedna ma błąd, chcemy mieć 19 udanych i wiedzieć, której brakuje. Nie chcemy stracić wszystkich z powodu jednej awarii.

Mamy dwie strategie, żeby to naprawić. W Ćwiczeniu 2 napiszemy obie i porównamy.

::: {.callout-note}
## Checkpoint
1. Uruchom skrypt kilka razy. Jak często trafia w gałąź `Pobrano 20 stron`? (Powinno: raz na ~1200 prób. Praktycznie nigdy nie zobaczysz.)
2. Co dokładnie zwraca `r.raise_for_status()` przy 500? (`httpx.HTTPStatusError`. To podklasa `httpx.HTTPError`, którą można łapać szerzej.)
3. Spróbuj wstawić `print("zwracam dane")` na końcu `fetch_page`, tuż przed `return`. Uruchom przy 5 powtórzeniach. Czy te printy pojawiają się dla **udanych** korutyn, gdy zostanie podniesiony wyjątek przez nieudaną? (Tak - korutyny, które już skończyły, zwracają dane normalnie. Tracimy je nie dlatego, że nie powstały, tylko dlatego, że `gather` ich nie zwraca po wyjątku.)
:::

---

# Ćwiczenie 2: dwie strategie obsługi błędów

Mamy dwa idiomy. **Pierwszy** zostawia korutynę nietkniętą i mówi `gather`-owi, żeby **nie przerywał** na wyjątkach, tylko zwrócił je w liście wyników. **Drugi** opakowuje błąd już w korutynie, tak by `gather` nigdy nie zobaczył wyjątku - tylko zwykłą wartość zwrotną mówiącą „sukces" lub „porażka".

Napiszemy obie wersje na tym samym serwerze (`/flaky`) i porównamy, kiedy która jest naturalna.

## Krok A: `return_exceptions=True`

Utwórz plik `cw2a.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 20
START = None


async def fetch_page(client, page):
    r = await client.get(f"{BASE}/flaky/{page}")
    r.raise_for_status()
    return r.json()


async def main():
    async with httpx.AsyncClient() as client:
        coros = [fetch_page(client, p) for p in range(N)]
        # 1. Wywołaj asyncio.gather z parametrem return_exceptions=True.
        #    Dzięki temu gather nie przerwie się na wyjątkach -
        #    zwróci je w liście wyników na odpowiadających pozycjach.
        # --- Twój kod ---
        return ...


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START

# 2. Rozdziel wyniki na sukcesy i porażki.
#    Wyniki to lista długości N. Element na pozycji i odpowiada żądaniu o page=i.
#    Jeśli element jest instancją Exception - to była porażka.
#    W przeciwnym razie - sukces (dict z polami page, items).
sukcesy = ...    # --- Twój kod ---
porazki = ...    # --- Twój kod ---

# 3. Wypisz raport:
#    - łączny czas,
#    - liczbę sukcesów i liczbę porażek,
#    - dla każdej porażki: numer strony i typ wyjątku.
# --- Twój kod ---
```

Uruchom. Spodziewany wynik:

```
Czas: 1.05s   sukcesy: 14   porażki: 6
Porażka page=2 : HTTPStatusError
Porażka page=5 : HTTPStatusError
Porażka page=11: HTTPStatusError
...
```

Konkretne liczby (14 vs 6) będą się różnić - są losowe. Ważne, że **wszystkie 20 żądań** doszło do skutku i mamy zarówno udane wyniki, jak i informację, czego nie udało się pobrać.

::: {.callout-tip}
## `return_exceptions=True` - mocne i słabe strony
**Plusy**: 

* minimalna zmiana w stosunku do naiwnego `gather`. Jeden parametr i pętla rozdzielająca wyniki.
* zachowuje korespondencję pozycyjną - element na pozycji `i` odpowiada żądaniu `i`. Łatwo połączyć wyniki z wejściowymi parametrami.

**Minusy**

* typ elementów listy jest zmienny - albo `dict`, albo `Exception`. Każdy kod, który chce z tego korzystać, musi sprawdzić `isinstance`.
* trudno przekazać dodatkową informację o tym, **co dokładnie** zawiodło. Wyjątek niesie tylko stack trace; jeśli chcesz wiedzieć, której strony dotyczył, musisz patrzeć na pozycję na liście.
:::

## Krok B: `try/except` w korutynie

Druga strategia: ucz korutynę zwracać `dict` z polem `"status"`, niezależnie od tego, czy żądanie się udało.

Utwórz plik `cw2b.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 20
START = None


async def fetch_page(client, page):
    """Zawsze zwraca dict. Nigdy nie rzuca wyjątku."""
    # 1. Wewnątrz try wykonaj GET na /flaky/<page>, sprawdź status,
    #    zwróć słownik o kształcie:
    #      {"status": "ok", "page": page, "data": r.json()}
    # 2. W except httpx.HTTPStatusError zwróć słownik:
    #      {"status": "err", "page": page, "error": "HTTP_" + str(e.response.status_code)}
    #    (Inne typy błędów też można łapać - np. httpx.RequestError - na tę chwilę
    #    /flaky rzuca tylko HTTPStatusError.)
    # --- Twój kod ---
    ...


async def main():
    async with httpx.AsyncClient() as client:
        coros = [fetch_page(client, p) for p in range(N)]
        return await asyncio.gather(*coros)


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START

# 3. Rozdziel wyniki przez kolejną zwykłą iterację - już bez isinstance,
#    bo wszystkie elementy to dict-y. Filtrujesz po kluczu "status":
sukcesy = [r for r in wyniki if r["status"] == "ok"]
porazki = [r for r in wyniki if r["status"] == "err"]

print(f"Czas: {elapsed:.2f}s   sukcesy: {len(sukcesy)}   porażki: {len(porazki)}")
for p in porazki:
    print(f"  page={p['page']:2d}  {p['error']}")
```

Uruchom. Wynik jest tej samej postaci co w cw2a - inne dokładne liczby, ten sam kształt:

```
Czas: 1.04s   sukcesy: 13   porażki: 7
  page= 1  HTTP_500
  page= 4  HTTP_500
  ...
```

::: {.callout-tip}
## `try/except` w korutynie - mocne i słabe strony
**Plusy**: 

* wszystkie wyniki są tego samego typu. Kod, który je przetwarza, nie musi się rozglądać za wyjątkami.
* korutyna ma kontekst (parametry wywołania), więc może wpisać do wyniku **rzeczowe** informacje - numer strony, URL, typ błędu, kod statusu. Wyjątek sam z siebie tego nie zawiera.
* łatwo dodać logikę pośrednią - np. retry przed zwróceniem porażki, ograniczenie tekstu błędu, normalizację formatu.

**Minus**: korutyna musi wiedzieć, że ma „nie psuć". Łatwo zapomnieć i puścić nowy typ wyjątku, którego nie złapie nasz `except`. Wtedy `gather` go znowu propaguje - i wracamy do Demonstracji 3.
:::

::: {.callout-note}
## Kiedy co
Reguła praktyczna z tego labu:

* **`return_exceptions=True`** - prototyp, eksperymentowanie, jednorazowe skrypty. Krótszy kod.
* **`try/except` w korutynie** - kod produkcyjny, długie pipelines, wiele etapów przetwarzania. Lepsza struktura wyników.

W Ćwiczeniu 5 używamy wariantu drugiego - bo nasz pipeline ma raport końcowy z konkretnymi numerami stron, kategoriami błędów itd. Wymagałoby to dwukrotnie tyle kodu z `return_exceptions=True`.
:::

::: {.callout-note}
## Checkpoint
1. Czy w obu wariantach `cw2a` i `cw2b` liczba sukcesów + liczba porażek to dokładnie `N = 20`? Powinno tak być.
2. W `cw2b` - co się stanie, gdy serwer dorzuci nowy typ błędu, którego twój `except` nie łapie (np. `httpx.RequestError` przy zerwanym połączeniu)? Wypróbuj: w `app.py` zmień jeden z endpointów na `return jsonify({"error": "x"}), 503`, dodaj do `fetch_page` `except httpx.HTTPStatusError` i sprawdź, czy korutyna nadal nie wpada w nieprzewidziany wyjątek.
3. Spróbuj rozszerzyć `cw2b` o pole `"latency"` - mierzony w korutynie czas wykonania pojedynczego żądania. Sukcesy i porażki powinny mieć to pole. Czy znacznie zmieniłeś strukturę kodu? (Powinno być proste - `try/except` w korutynie ma cały lokalny kontekst do dyspozycji.)
:::

---

# Ćwiczenie 3: timeouty

W Demonstracji 3 wszystkie żądania - i te udane, i te z błędem 500 - **wracały po ~1 s**. To jest komfortowy przypadek. Realny scraping bywa mniej miły: żądanie może trwać 30 s, minutę, nigdy się nie zakończyć.

Niektóre z tych „niekończących się" żądań naprawdę nigdy nie wrócą (serwer się zawiesił, sieć zerwała). Inne wrócą po długim czasie - ale po czasie tak długim, że na to nie chcemy czekać. W obu sytuacjach narzędziem jest **timeout**: jednostronne wycofanie się z czekania po określonym czasie.

W `httpx` timeout można ustawić na kliencie (jako domyślny) albo na pojedyncze żądanie (nadpisuje domyślny). Gdy serwer nie odpowie w zadanym czasie, `httpx` rzuca `httpx.TimeoutException`. To jest **kolejny typ wyjątku**, który warto obsłużyć - taki sam mechanizm jak w cw2b.

Endpoint do dzisiejszego ćwiczenia to `/slow/<page>` - opóźnienie losowe od 0.5 do 4 s. Ustawimy timeout na 1.5 s - czyli wszystko poniżej tego progu się uda, wszystko powyżej padnie z `TimeoutException`. Probabilistycznie powinno timeoutować ~71% żądań ($(4{-}1.5)/(4{-}0.5)$). To dużo - i o to chodzi: chcemy wyraźnie zobaczyć efekt.

Utwórz plik `cw3.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 20
TIMEOUT = 1.5
START = None


async def fetch_page(client, page):
    """Zawsze zwraca dict. Łapie HTTPStatusError i TimeoutException."""
    # 1. Wewnątrz try wykonaj GET na /slow/<page> z timeoutem TIMEOUT.
    #    Możesz przekazać timeout do client.get(..., timeout=TIMEOUT)
    #    albo ustawić go raz przy tworzeniu klienta (poniżej, w main).
    #    Zwróć słownik:
    #      {"status": "ok", "page": page, "data": r.json()}
    # 2. W except httpx.HTTPStatusError zwróć:
    #      {"status": "err", "page": page, "error": "HTTP_" + str(e.response.status_code)}
    # 3. W except httpx.TimeoutException zwróć:
    #      {"status": "err", "page": page, "error": "TIMEOUT"}
    # --- Twój kod ---
    ...


async def main():
    # Możesz ustawić timeout raz, dla całego klienta - wtedy wszystkie żądania
    # przez tego klienta będą go dziedziczyć.
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        coros = [fetch_page(client, p) for p in range(N)]
        return await asyncio.gather(*coros)


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START

sukcesy = [r for r in wyniki if r["status"] == "ok"]
timeouty = [r for r in wyniki if r.get("error") == "TIMEOUT"]
http_err = [r for r in wyniki if r.get("error", "").startswith("HTTP_")]

print(f"Czas: {elapsed:.2f}s")
print(f"  sukcesy:   {len(sukcesy):2d}")
print(f"  timeouty:  {len(timeouty):2d}")
print(f"  HTTP err:  {len(http_err):2d}")
```

Uruchom. Spodziewany wynik:

```
Czas: 1.55s
  sukcesy:   6
  timeouty:  14
  HTTP err:  0
```

Konkretne liczby będą się różnić - są losowe. Ważne dwie obserwacje:

* **Łączny czas to ~1.5 s, czyli `TIMEOUT`.** Sukcesy wracają w czasie 0.5-1.5 s, porażki wracają **dokładnie po `TIMEOUT`** (`httpx` przerywa czekanie po tym czasie). Żadne pojedyncze żądanie nie trwa dłużej niż `TIMEOUT` - to jest gwarancja, którą daje timeout.
* **Bez timeoutu** najwolniejsze żądanie zajęłoby do 4 s i tak długo musielibyśmy czekać na `gather`. Z timeoutem - 1.5 s plus odrobina. Timeout to **świadoma rezygnacja** z części wyników w zamian za przewidywalny czas zakończenia całej operacji.

::: {.callout-warning}
## Timeout jest nieodzowny przy `Semaphore`
Wyobraź sobie `Semaphore(10)` i bez-timeoutowego klienta. Jedno żądanie trafia na zawieszony serwer i wisi w nieskończoność. Pozostałe 9 miejsc w semaforze nadal działa - przepuszczają kolejne korutyny normalnie. Pipeline działa wolniej, ale działa.

Zawieszone żądanie **nigdy nie zwraca wyniku**, a `gather` czeka na **wszystkie** korutyny. Skrypt pobiera 99 stron, drukuje raport, i wisi w nieskończoność na setnej. Z poziomu terminala wygląda to identycznie jak zawieszenie — Ctrl-C jest jedynym wyjściem.

Drugi scenariusz: zawiesza się nie jedno żądanie, tylko kilka. Każde stałe zajmuje miejsce w semaforze. Efektywny limit spada z 10 do 9, do 5, w pesymistycznym przypadku do 0. Pipeline nie staje od razu — eroduje stopniowo, aż utyka.

W obu przypadkach lekarstwo jest to samo. **Zawsze ustawiaj timeout** — co najmniej w postaci `httpx.AsyncClient(timeout=30.0)`. Timeout zamienia „wisi w nieskończoność" na „rzuca `TimeoutException` po N sekundach", które twój `try/except` w korutynie obsłuży tak samo jak każdy inny błąd.
:::

::: {.callout-tip}
## `client.get(..., timeout=X)` vs `httpx.AsyncClient(timeout=X)`
Oba sposoby działają. Różnica:

* `httpx.AsyncClient(timeout=X)` - **domyślny timeout** dla wszystkich żądań przez tego klienta. Najlepsze do globalnego limitu.
* `client.get(url, timeout=X)` - **timeout na konkretne żądanie**, nadpisuje domyślny. Przydatne, gdy chcesz dać więcej czasu wybranym endpointom (np. „lista" 5 s, „detal" 1 s).

W praktyce: na kliencie ustaw rozsądne domyślne (10-30 s), a per-żądanie skracaj, gdy wiesz, że konkretny endpoint **musi** odpowiedzieć szybko (np. health check).
:::

::: {.callout-note}
## Checkpoint
1. Czy łączny czas wykonania jest bliski `TIMEOUT` (1.5 s) z drobnym ogonem? Jeśli wyraźnie więcej - sprawdź, czy `timeout` faktycznie został ustawiony (np. w `AsyncClient`) i czy korutyna nie próbuje retry-ować w cichym tle.
2. Zmień `TIMEOUT = 3.5`. Ile teraz jest sukcesów, ile timeoutów? (Powinno być znacznie więcej sukcesów, mniej timeoutów - $\approx (3.5-0.5)/3.5 \approx 86\%$ powinno się zmieścić.)
3. Zmień `TIMEOUT = 0.4`. Co się dzieje? (Wszystkie timeoutują - minimalne opóźnienie `/slow` to 0.5 s, czyli żadne nie zdąży.) Łączny czas? (~0.4 s. Pipeline kończy się błyskawicznie - z samymi porażkami.)
:::

---

# Ćwiczenie 4: `as_completed` - wyniki w miarę spływania

`gather` zwraca wszystkie wyniki **na raz**, gdy wszystkie korutyny się skończą. To wygodne, gdy chcesz mieć finalną listę. Ale gdy zadań jest dużo i niektóre są wolne, oznacza to długie milczenie aż do końca - bez sygnału, że cokolwiek się dzieje.

`asyncio.as_completed` rozwiązuje ten problem: zamiast czekać na wszystkie, zwraca **iterator**, który daje wyniki w **kolejności kończenia się** poszczególnych korutyn. Pierwsza skończona korutyna jest pierwsza w iteracji.

W tym ćwiczeniu wyświetlamy postęp na żywo, używając `/slow` (losowe opóźnienia) - tak by kolejność kończenia była wyraźnie inna od kolejności startów.

Utwórz plik `cw4.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
N = 20
LIMIT = 8
TIMEOUT = 5.0
START = None


async def fetch_page(client, page, sem):
    """Zawsze zwraca dict. Mierzy własną latencję."""
    async with sem:
        t0 = time.perf_counter()
        try:
            r = await client.get(f"{BASE}/slow/{page}")
            r.raise_for_status()
            latency = time.perf_counter() - t0
            return {"status": "ok", "page": page, "latency": latency, "data": r.json()}
        except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
            latency = time.perf_counter() - t0
            return {"status": "err", "page": page, "latency": latency, "error": str(e)}


async def main():
    sem = asyncio.Semaphore(LIMIT)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        coros = [fetch_page(client, p, sem) for p in range(N)]
        wyniki = []
        # 1. Iteruj przez asyncio.as_completed(coros), używając enumerate
        #    od 1, żeby śledzić numer zakończonego zadania.
        # 2. Wewnątrz pętli:
        #      - await fut, dołóż wynik do listy wyniki,
        #      - zmierz czas globalny: t = time.perf_counter() - START,
        #      - wypisz linijkę z polami: numer w iteracji, t, page,
        #        status i latency z wyniku.
        #    Sugerowany format printa:
        #      [#{i:2d}/{N}]  t={t:5.2f}s  page={r['page']:2d}  status={r['status']:3s}  latency={r['latency']:.2f}s
        # 3. Zwróć listę wyniki.
        # --- Twój kod ---
        return wyniki


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START

sukcesy = [r for r in wyniki if r["status"] == "ok"]
print(f"\nCzas: {elapsed:.2f}s   sukcesy: {len(sukcesy)}/{N}")
```

Uruchom. Spodziewany wynik (konkretne liczby losowe):

```
[# 1/20]  t= 0.66s  page= 3  status=ok  latency=0.66s
[# 2/20]  t= 0.81s  page= 0  status=ok  latency=0.81s
[# 3/20]  t= 1.13s  page= 5  status=ok  latency=1.13s
[# 4/20]  t= 1.42s  page= 6  status=ok  latency=1.42s
[# 5/20]  t= 1.79s  page= 2  status=ok  latency=1.79s
[# 6/20]  t= 1.83s  page= 8  status=ok  latency=0.40s
...
[#20/20]  t= 7.21s  page=15  status=ok  latency=2.10s

Czas: 7.22s   sukcesy: 20/20
```

Cztery rzeczy do zauważenia:

* **`page=3` skończyło się pierwsze, mimo że było czwarte w kolejce.** Kolejność wyników w iteracji nie ma związku z kolejnością wejściową - jest to kolejność losowych opóźnień serwera.
* **Postęp jest widoczny na żywo.** Każda linijka pojawia się w chwili, gdy odpowiadająca korutyna kończy. To radykalna różnica względem `gather`, który drukuje wszystko dopiero na końcu.
* **Pierwsze 8 startów dzieje się równolegle** (`Semaphore(8)`); ósme zakończenie zwalnia miejsce, dziewiąta korutyna może wystartować. Widać to po polu `latency` - pierwsze 8 ma latency mniej więcej równe `t`, kolejne mają niższe latency niż `t`, bo czekały w semaforze, zanim faktycznie wystartowały żądanie.
* **Łączny czas to ~7 s.** Średnia latency `/slow` to 2.25 s; przy `LIMIT=8` mamy ~3 paczki, każda średnio 2.25 s plus końcowy ogon najwolniejszych - razem rząd 7 s.

::: {.callout-warning}
## `as_completed` traci kolejność wejściową
Lista `wyniki` zbudowana wewnątrz pętli `for fut in as_completed(...)` nie ma korespondencji pozycyjnej z `range(N)`. Element `wyniki[0]` to **najszybciej zakończona** korutyna, nie pierwsza w kolejce.

Jak temu zaradzić, jeśli kolejność wejściowa jest potrzebna? Dwa idiomy:

* **Wbij identyfikator w wynik** - tak jak my dzisiaj (pole `page`). Wyniki nadal są w kolejności kończenia, ale każdy „wie", do której pozycji wejściowej należy.
* **Sortuj po fakcie** - po `key=lambda r: r["page"]`. Iteracja `as_completed` daje wyniki w kolejności kończenia, sortowanie po pobraniu wszystkich daje porządek wejściowy.

`gather` z `return_exceptions` zachowuje kolejność wejściową **z założenia** - to jest jej kompromis: brak postępu na żywo w zamian za prostą strukturę wyników.
:::

::: {.callout-tip}
## `as_completed` vs `gather` - decyzja
* **`gather(*coros)`** - chcesz mieć listę wyników w kolejności wejściowej, nie zależy ci na bieżącym podglądzie. Krótszy kod.
* **`asyncio.as_completed(tasks)`** - chcesz pokazywać użytkownikowi postęp, masz długie zadania, dane szybkie zaczynają napływać i można je zacząć przetwarzać. Też przydatne, gdy chcesz przerwać po pierwszych N sukcesach (np. „pobierz 5 dowolnych źródeł", gdzie nie ma znaczenia, które konkretnie).
:::

::: {.callout-note}
## Checkpoint
1. Czy w twoim wyjściu strona z najniższą wartością `latency` w pierwszych 8 wynikach (czyli ta, która szybko zwolniła miejsce w semaforze) była **wcześniej** w `range(N)` niż strona z najwyższą `latency`? Niekoniecznie - losowość serwera to przykrywa.
2. Zmień `LIMIT = 1`. Co teraz pokazuje pole `latency` względem `t`? (Powinny być sobie równe - każda korutyna od razu po wejściu do semafora startuje żądanie, nikt nie czeka.) Łączny czas? (Suma wszystkich latency, czyli ~45 s. Możesz przerwać Ctrl-C.)
3. Zmień `LIMIT = 20` (równe `N`). Czas? (Maksymalna latency, ~4 s - wszystkie startują od razu, kończą się w naturalnej kolejności opóźnień.) Czy widać teraz **drugą falę** żądań w printach? (Nie - nie ma drugiej fali, wszystko mieści się w jednej.)
:::

---

# Ćwiczenie 5: pełen pipeline

Składamy wszystkie elementy. Pobieramy zestaw 50 żądań - 25 do `/flaky` i 25 do `/slow` - z kontrolą współbieżności (`Semaphore`), timeoutem, obsługą błędów (`try/except` w korutynie) i postępem na żywo (`as_completed`). Sukcesy lądują w jednym pliku JSON, porażki w drugim. Na koniec wypisujemy raport.

To jest scenariusz odpowiadający realnemu zadaniu scrapingu listy URL-i z różnych źródeł: część odpowiada szybko i poprawnie, część rzuca błędem, część jest zbyt wolna na nasz timeout, część wisi.

Utwórz plik `cw5.py`:

```python
import asyncio
import json
import time

import httpx

BASE = "http://127.0.0.1:5000"
LIMIT = 8
TIMEOUT = 3.0
START = None


def make_url_list():
    """Buduje listę 50 URL-i: 25 do /flaky, 25 do /slow."""
    urls = []
    for page in range(25):
        urls.append(("flaky", page, f"{BASE}/flaky/{page}"))
    for page in range(25):
        urls.append(("slow", page, f"{BASE}/slow/{page}"))
    return urls


async def fetch_one(client, kind, page, url, sem):
    """Pobiera jeden URL. Zawsze zwraca dict opisujący wynik."""
    async with sem:
        t0 = time.perf_counter()
        try:
            r = await client.get(url)
            r.raise_for_status()
            return {
                "status": "ok",
                "kind": kind,
                "page": page,
                "url": url,
                "latency": round(time.perf_counter() - t0, 3),
                "data": r.json(),
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "err",
                "kind": kind,
                "page": page,
                "url": url,
                "latency": round(time.perf_counter() - t0, 3),
                "error": f"HTTP_{e.response.status_code}",
            }
        except httpx.TimeoutException:
            return {
                "status": "err",
                "kind": kind,
                "page": page,
                "url": url,
                "latency": round(time.perf_counter() - t0, 3),
                "error": "TIMEOUT",
            }


async def main():
    sem = asyncio.Semaphore(LIMIT)
    urls = make_url_list()
    total = len(urls)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        tasks = [
            fetch_one(client, kind, page, url, sem)
            for kind, page, url in urls
        ]
        # 1. Iteruj przez asyncio.as_completed(tasks) z enumerate od 1.
        # 2. Dla każdego ukończonego zadania:
        #      - await fut, dodaj do listy wyniki,
        #      - wypisz krótki postęp: numer, czas globalny, kind, page, status.
        # 3. Zwróć listę wyniki.
        wyniki = []
        # --- Twój kod ---
        return wyniki


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START

# Podział wyników
sukcesy = [r for r in wyniki if r["status"] == "ok"]
porazki = [r for r in wyniki if r["status"] == "err"]

# Zapis
with open("wyniki.json", "w", encoding="utf-8") as f:
    json.dump(sukcesy, f, ensure_ascii=False, indent=2)
with open("bledy.json", "w", encoding="utf-8") as f:
    json.dump(porazki, f, ensure_ascii=False, indent=2)

# Raport
http_err = sum(1 for r in porazki if r["error"].startswith("HTTP_"))
timeouty = sum(1 for r in porazki if r["error"] == "TIMEOUT")
flaky_ok = sum(1 for r in sukcesy if r["kind"] == "flaky")
slow_ok = sum(1 for r in sukcesy if r["kind"] == "slow")

print("\n=== RAPORT ===")
print(f"Łączny czas:    {elapsed:.2f}s")
print(f"Wszystkich:     {len(wyniki)}")
print(f"  sukcesy:      {len(sukcesy)} ({flaky_ok} flaky, {slow_ok} slow)")
print(f"  porażki:      {len(porazki)} ({http_err} HTTP, {timeouty} TIMEOUT)")
print(f"\nZapisano: wyniki.json ({len(sukcesy)} rekordów), bledy.json ({len(porazki)} rekordów)")
```

Uruchom. Spodziewany wynik (konkretne liczby losowe):

```
[# 1/50]  t= 0.86s  flaky/12  ok
[# 2/50]  t= 0.91s  flaky/ 4  ok
[# 3/50]  t= 1.03s  flaky/ 0  ok
[# 4/50]  t= 1.03s  flaky/ 1  ok
[# 5/50]  t= 1.04s  flaky/ 7  err
...
[#50/50]  t=10.34s  slow/22   ok

=== RAPORT ===
Łączny czas:    10.35s
Wszystkich:     50
  sukcesy:      35 (17 flaky, 18 slow)
  porażki:      15 (8 HTTP, 7 TIMEOUT)

Zapisano: wyniki.json (35 rekordów), bledy.json (15 rekordów)
```

Otwórz oba pliki w VSCode i zerknij na zawartość. `wyniki.json` zawiera słowniki z polem `"data"` (rzeczywiste odpowiedzi serwera). `bledy.json` zawiera słowniki z polem `"error"` (typ porażki) i `"latency"` (kiedy się wycofaliśmy).

To jest fundament pipeline'u scrapingu: niezależnie od tego, jak źle zachowa się serwer i sieć, twój skrypt **kończy w przewidywalnym czasie** (ograniczonym przez `TIMEOUT` i liczbę paczek z `Semaphore`) i **niczego nie traci**. Wszystko trafia albo do sukcesów, albo do porażek - z pełnym kontekstem do późniejszej analizy lub ponowienia.

::: {.callout-tip}
## Co tu jest produkcyjnego, a co laboratoryjnego
**Produkcyjne wzorce** (zostają w realnym kodzie):

* `Semaphore` z rozsądnym limitem,
* timeout na kliencie,
* `try/except` w korutynie zwracający strukturalny wynik,
* zapis sukcesów i porażek osobno,
* raport z liczbami.

**Laboratoryjne uproszczenia** (w realu rozbudowujesz):

* lista URL-i konstruowana w kodzie - w realu czytasz ją z pliku, bazy, kolejki,
* tylko dwa typy błędów obsłużone - w realu jeszcze `httpx.RequestError` (połączenie), `httpx.DecodingError` (zła odpowiedź), być może własne wyjątki domenowe,
* brak retry - patrz Ćwiczenie samodzielne B,
* brak logowania - w realu zamiast `print` używasz `logging` z poziomami INFO/WARNING/ERROR.

Wzorzec jednak się nie zmienia. Bazą jest tych ~30 linijek `fetch_one` z pełnym `try/except` plus `as_completed` z postępem.
:::

::: {.callout-note}
## Checkpoint
1. Czy `len(sukcesy) + len(porazki) == 50`? Musi być.
2. Otwórz `wyniki.json`. Czy każdy rekord ma pola `kind`, `page`, `url`, `latency`, `data`? A `bledy.json` - czy ma `error` zamiast `data`?
3. Zmień `TIMEOUT = 1.0`. Ile teraz timeoutów? (Powinno być znacznie więcej - większość `/slow` nie zdąży.) Zmień `TIMEOUT = 5.0`. Ile teraz? (Niewielu timeoutów - tylko najbardziej pechowe pojedyncze przypadki.) Czas wykonania?
4. Co by się stało, gdyby zamiast `as_completed` użyć `gather` (bez `return_exceptions`)? Czy w tym kodzie potrzebujemy `return_exceptions=True`? (Nie - korutyna `fetch_one` nie rzuca już żadnego wyjątku. Każdy `try/except` jest złapany wewnątrz. `gather` widzi 50 grzecznych korutyn, które zawsze zwracają dict.)
:::

---

# Ćwiczenia samodzielne

## Ćwiczenie A: krzywa wydajności

Napisz skrypt `cwA_krzywa.py`, który:

1. Dla `N = 100` żądań do `/data` mierzy czas wykonania przy `LIMIT ∈ {1, 2, 5, 10, 20, 50, 100}`.
2. Wypisuje tabelkę: `limit` | `czas` | `przyspieszenie vs limit=1`.
3. Komentuje wynikową krzywą jednym zdaniem - od którego momentu dalsze zwiększanie `LIMIT` nie daje przyspieszenia, i dlaczego.

Powtórz to samo dla `/limited`. Jakie są dwie różnice w kształcie krzywej?

## Ćwiczenie B: async retry z backoffem

W Lab 2 napisałeś `fetch_with_retry` w wersji synchronicznej - z `requests`, `time.sleep` i pętlą `for attempt in range(max_attempts)`. Przenieś ten sam wzorzec do `asyncio`.

Napisz korutynę `fetch_with_retry_async(client, url, max_attempts=3, base_delay=0.5)`, która:

1. Próbuje pobrać `url` przez `client`.
2. Przy błędzie 5xx **lub** timeoucie ponawia próbę z opóźnieniem `base_delay * 2 ** attempt` (`await asyncio.sleep`, nie `time.sleep`!).
3. Przy błędzie 4xx (poza 429) **nie ponawia** - to są błędy klienta, nie poprawi ich powtórka.
4. Po wyczerpaniu prób zwraca strukturalny błąd jak w Ćw 5.

Test: pobierz 50 razy `/flaky` z `Semaphore(8)`, `TIMEOUT=2.0`, `max_attempts=3`. Powinno udać się prawie wszystko - prawdopodobieństwo, że trzy kolejne próby z rzędu padną, to $0.3^3 \approx 2.7\%$, czyli statystycznie 1-2 trwałe porażki na 50.

## Ćwiczenie C: async pipeline na realnym API

Wróć do Labu 2 i przepisz `fetch_all_datasets` w wersji async, używając `httpx.AsyncClient` zamiast `requests`. Przygotuj się na trzy decyzje:

1. **Semaphore.** Dane są publiczne, ale serwer (`api.dane.gov.pl`) jest produkcyjny - nie nasz. Zacznij od `Semaphore(5)`. Wyżej nie idź bez bardzo dobrego powodu.
2. **Timeout.** Realny serwer bywa wolniejszy niż lokalny - daj `TIMEOUT = 10.0` jako wyjściowe ustawienie.
3. **Stronicowanie.** W Labie 2 stronicowanie było sekwencyjne („pobierz stronę, zerknij na `links.next`, pobierz następną"). W async to się **psuje**: nie wiemy, ilu stron jest, dopóki nie pobierzemy pierwszej. Strategia mieszana: pobierz stronę 1 sekwencyjnie, sprawdź `meta.total`, oblicz liczbę stron, **pozostałe pobierz przez `gather`**.

Porównaj czas wersji sync (Lab 2) z async. Spodziewaj się przyspieszenia proporcjonalnego do liczby stron (`Semaphore` może ograniczyć - to celowe, nie zwiększaj).

To jest jedyne ćwiczenie tego labu, które wychodzi poza lokalny serwer. Argumentacja: API `dane.gov.pl` jest publiczne, znane z Labu 1-2 i wytrzymuje rozsądną liczbę zapytań. `Semaphore(5)` jest tu gwarantem grzeczności.

---

# Podsumowanie

W tym labie:

* zobaczyłeś, że **naiwne `gather` na 100 żądaniach** działa w warunkach laboratoryjnych, ale w realiach scrapingu jest nieakceptowalne - serwer ma własne limity, rate limiting i mechanizmy obrony,
* opanowałeś **`asyncio.Semaphore`** jako standardowy ogranicznik współbieżności po stronie klienta - tworzony raz w `main`, przekazywany do wszystkich korutyn, używany w bloku `async with sem:`,
* zdiagnozowałeś **limit po stronie serwera** - na `/limited` z `SERVER_SEM(8)` widać kolano w czasie wykonania: zwiększanie `LIMIT` powyżej 8 nic nie daje, bo wąskim gardłem przestaje być klient,
* poznałeś **dwie strategie obsługi błędów** w `gather`: `return_exceptions=True` (krótsze, dla prototypów) i `try/except` w korutynie (lepsza struktura wyników, do produkcyjnego kodu),
* poznałeś **timeouty w `httpx`** jako mechanizm gwarantujący przewidywalny czas wykonania - oraz zasadę „timeout + `Semaphore` to para nierozłączna",
* zbudowałeś klienta z **`as_completed`**, który pokazuje postęp na żywo - i zauważyłeś, że traci kolejność wejściową, którą trzeba odzyskać przez identyfikator w wyniku lub sortowanie po fakcie,
* złożyłeś wszystkie klocki w **pełen pipeline** (Ćw 5): 50 mieszanych żądań, kontrola współbieżności, timeout, obsługa błędów, podział wyników na sukcesy i porażki, raport końcowy.

Mapa decyzji, którą warto zapamiętać:

| Sytuacja | Narzędzie |
|---|---|
| Chcesz uruchomić N korutyn naraz i mieć wszystkie wyniki w kolejności wejściowej | `gather` |
| Chcesz pokazać postęp na żywo, przerwać po pierwszych N, mieć wyniki w kolejności kończenia | `as_completed` |
| Chcesz uniknąć przeciążenia serwera lub klienta | `Semaphore(N)` |
| Chcesz mieć gwarancję czasu zakończenia każdego żądania | `timeout` (na kliencie albo per-żądanie) |
| Chcesz dostać wszystkie wyniki, łącznie z błędami, w prostej liście | `gather(..., return_exceptions=True)` |
| Chcesz mieć strukturalne wyniki z kontekstem (numer strony, typ błędu, latency) | `try/except` w korutynie, zwracający `dict` |

**Co dalej:**

* **Wykład 6**: Scrapy - framework do scrapingu. Wszystko, co dziś składaliśmy ręcznie (kontrola współbieżności, retry, kolejki, obsługa błędów, zapis do JSON/CSV) Scrapy daje gotowe. Z naszej perspektywy: konfigurujesz `DOWNLOAD_DELAY`, `CONCURRENT_REQUESTS`, `RETRY_TIMES` i piszesz tylko logikę specyficzną dla strony.
* **Lab 11**: pierwszy spider Scrapy na lokalnym serwerze. Porównanie ręcznego crawlera (Lab 4) z wersją w Scrapy - ten sam serwer, ten sam rezultat, znacznie mniej kodu.
* **Lab 12**: pipeline Scrapy z paginacją i studium przypadku na realnej stronie.
