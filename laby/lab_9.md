---
title: "Lab 9: Async od zera"
subtitle: "Automatyczne pozyskiwanie danych - ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Korutyna jako „obietnica wykonania" - `async def`, `await`, `asyncio.run()` jako jedyny punkt wejścia,
* Pętla `await` jest sekwencyjna - sam `await` niczego nie przyspiesza, jeśli nie ma między czym przełączać,
* `asyncio.gather` jako podstawowy mechanizm współbieżności wielu korutyn,
* `asyncio.create_task` jako bardziej elementarny budulec - rejestracja bez czekania,
* Pułapka `time.sleep` w korutynie - synchroniczne wywołanie blokuje cały event loop,
* Pierwszy klient async HTTP z `httpx.AsyncClient` - porównanie sync vs async na tym samym zadaniu (10 stron, ~10 s vs ~1 s),
* Wizualizacja przeplotu startów i zakończeń przez logowanie postępu z `time.perf_counter()`.

Narzędzia: Python (`asyncio`, `httpx`, `requests`, Flask), VSCode.

---

# Przygotowanie

Środowisko jak na poprzednich labach: VSCode, dwa terminale.

Sprawdź, czy potrzebne pakiety są dostępne, i w razie potrzeby zainstaluj brakujące:

```bash
pip install flask requests httpx
```

::: {.callout-tip}
## Instalacja pakietów w pracowni
Komputery w pracowni mogą resetować pakiety między sesjami. Na początku każdego labu sprawdź, czy potrzebne pakiety są dostępne, i w razie potrzeby zainstaluj je ponownie. `httpx` jest nowy w tym labie - wcześniej go nie używaliśmy.
:::

Utwórz folder `lab9/` i otwórz go w VSCode. **Terminal 2** otwórz w `lab9/` - tam będziemy pisać klienta. **Terminal 1** otworzymy później (w Ćwiczeniu 3), gdy wystartujemy serwer Flask.

Każdy krok labu trafia do osobnego pliku - `demo1.py`, `cw1.py`, `cw3_async.py` itd. Dzięki temu, jeśli wrócisz do dowolnego kroku, masz go w czystym, izolowanym pliku.

---

# Wstęp: gdzie jesteśmy

Lab 8 zakończył pełen pipeline scrapingu chronionej strony: logowanie przez `requests.Session`, pobranie HTML, parsowanie BeautifulSoup. Trzy konta - sześć żądań sekwencyjnie, ~tyle czasu, ile sumują się odpowiedzi serwera. Działa, ale skaluje się liniowo: dziesięć kont to dwadzieścia żądań po kolei, sto kont to dwieście. Synchroniczny klient przez większość czasu **bezczynnie czeka** na odpowiedzi.

Wykład 5 pokazał, jak ten problem rozwiązać: zamiast czekać na każdą odpowiedź po kolei, **wysłać kolejne żądania w międzyczasie**. Mechanizm to event loop, składnia to `async def` / `await`, biblioteka to `httpx.AsyncClient`.

Dziś zbudujemy ten mechanizm od fundamentu. Pierwsze pięć kroków odbywa się **wyłącznie na `asyncio.sleep`** - bez sieci, bez serwera, bez HTTP. Skupiamy się na samym przepływie sterowania w `asyncio`. Dopiero w Ćwiczeniu 3 - gdy wzorzec jest opanowany - wstawiamy go w prawdziwego klienta sieciowego i porównujemy z wersją synchroniczną.

---

# Demonstracja 1: korutyna to nie zwykła funkcja

Utwórz plik `demo1.py`:

```python
import asyncio


async def fetch_page(page_id):
    print(f"  fetch_page({page_id}): start")
    await asyncio.sleep(1)
    print(f"  fetch_page({page_id}): koniec")
    return f"dane-{page_id}"


# Co się stanie, gdy wywołamy korutynę bez await?
print("=== Wywołanie bez await ===")
result = fetch_page(0)
print(f"Wynik: {result}")
print(f"Typ:   {type(result).__name__}")
```

Uruchom:

```bash
python demo1.py
```

Spodziewany wynik:

```
=== Wywołanie bez await ===
Wynik: <coroutine object fetch_page at 0x7f...>
Typ:   coroutine
sys:1: RuntimeWarning: coroutine 'fetch_page' was never awaited
```

Trzy obserwacje:

* **Print `fetch_page(0): start` się NIE pojawił.** Ciało funkcji w ogóle się nie wykonało.
* **`result` nie jest stringiem `dane-0`** - jest obiektem typu `coroutine`. Wywołanie korutyny zwraca *obietnicę wykonania*, nie sam wynik.
* **Python rzuca `RuntimeWarning`** - ostrzega, że stworzyliśmy korutynę i nigdy jej nie uruchomiliśmy. Z jego perspektywy to wyciek pracy.

Aby uruchomić korutynę, potrzebujemy event loopu. Dopisz na dole pliku:

```python
print("\n=== Wywołanie z asyncio.run ===")


async def main():
    result = await fetch_page(0)
    print(f"Wynik: {result}")


asyncio.run(main())
```

Spodziewany wynik (po uruchomieniu pliku ponownie):

```
=== Wywołanie bez await ===
Wynik: <coroutine object fetch_page at 0x7f...>
Typ:   coroutine
...

=== Wywołanie z asyncio.run ===
  fetch_page(0): start
  fetch_page(0): koniec
Wynik: dane-0
```

Tym razem ciało korutyny się wykonało. Trzy nowe elementy:

* **`async def main()`** - korutyna nadrzędna, czyli „program asynchroniczny" w kapsule.
* **`await fetch_page(0)`** - punkt zawieszenia. Mówi: „uruchom tę korutynę i zaczekaj na jej wynik".
* **`asyncio.run(main())`** - jedyny punkt wejścia. Tworzy event loop, uruchamia w nim `main()`, czeka na zakończenie i zamyka loop. Cały kod asynchroniczny żyje **wewnątrz** `asyncio.run()`.

::: {.callout-note}
## Checkpoint
1. Co dokładnie zwraca samo wywołanie `fetch_page(0)` (bez `await`)? Jaki ma typ?
2. Czy ciało korutyny wykonuje się w momencie jej wywołania, czy dopiero później?
3. Spróbuj **usunąć** słowo `await` przed `fetch_page(0)` wewnątrz `main()`. Co się dzieje? Dlaczego ostrzeżenie wraca?
:::

::: {.callout-tip}
## Dwa elementy, które idą w parze
`async def` deklaruje, że funkcja jest korutyną - zwraca obiekt `coroutine` zamiast wykonać ciało. `await` jest jedynym sposobem, by ten obiekt **wprawić w ruch**. Razem z `asyncio.run()` (na samym wierzchu programu) tworzą minimalny zestaw, bez którego asyncio nie ma sensu.
:::

---

# Demonstracja 2: pętla `await` jest sekwencyjna

Utwórz plik `demo2.py`:

```python
import asyncio
import time

START = None  # zostanie ustawione tuż przed asyncio.run


async def fetch_page(page_id):
    t0 = time.perf_counter() - START
    print(f"[t={t0:5.2f}s] START  page={page_id}")
    await asyncio.sleep(1)
    t1 = time.perf_counter() - START
    print(f"[t={t1:5.2f}s] DONE   page={page_id}")
    return f"dane-{page_id}"


async def main():
    for i in range(5):
        await fetch_page(i)


START = time.perf_counter()
asyncio.run(main())
elapsed = time.perf_counter() - START
print(f"\nŁącznie: {elapsed:.2f}s")
```

Uruchom. Spodziewany wynik:

```
[t= 0.00s] START  page=0
[t= 1.00s] DONE   page=0
[t= 1.00s] START  page=1
[t= 2.00s] DONE   page=1
[t= 2.00s] START  page=2
[t= 3.00s] DONE   page=2
[t= 3.00s] START  page=3
[t= 4.00s] DONE   page=3
[t= 4.00s] START  page=4
[t= 5.00s] DONE   page=4

Łącznie: 5.01s
```

Mamy `async def`, mamy `await`, mamy event loop - a program działa **dokładnie tak samo wolno** jak zwykła pętla z `time.sleep`. Pięć stron po sekundzie każda, łącznie pięć sekund. Kolejny `START` pojawia się dopiero po `DONE` poprzedniej strony.

Dlaczego? `await` mówi: „tu się zawieszam, mogę oddać sterowanie event loopowi". Ale event loop nie ma nic innego do roboty - w danym momencie jest **tylko jedna korutyna** do wykonania (ta, na którą czekamy). Czeka aż `fetch_page(0)` skończy się w całości, dopiero potem rusza `fetch_page(1)`.

Wniosek, który warto zapisać dużymi literami:

::: {.callout-warning}
## `async` to nie magia
Sam `await` w pętli **niczego nie przyspiesza**. Aby zyskać współbieżność, trzeba **zarejestrować wiele korutyn jednocześnie** - żeby event loop miał między czym przełączać, gdy jedna z nich się zawiesi.
:::

To jest centralne nieporozumienie początkujących z asyncio. Zaraz je rozwiążemy.

::: {.callout-tip}
## Logowanie postępu z `time.perf_counter()`
Trzy linijki, które pojawią się w każdym pliku tego labu:

```python
START = time.perf_counter()  # tuż przed asyncio.run
# ... w korutynie:
t0 = time.perf_counter() - START
print(f"[t={t0:5.2f}s] START  page={page_id}")
```

Daje czytelny **przeplot startów i zakończeń**. Nie wystarcza znać końcowy czas - trzeba widzieć, kiedy każda korutyna ruszyła i kiedy skończyła. Końcowa liczba (5.01s) mówi, że było wolno; przeplot mówi, *dlaczego*.
:::

---

# Ćwiczenie 1: `gather` - natychmiastowa współbieżność 

Utwórz plik `cw1.py`:

```python
import asyncio
import time

START = None


async def fetch_page(page_id):
    t0 = time.perf_counter() - START
    print(f"[t={t0:5.2f}s] START  page={page_id}")
    await asyncio.sleep(1)
    t1 = time.perf_counter() - START
    print(f"[t={t1:5.2f}s] DONE   page={page_id}")
    return f"dane-{page_id}"


async def main():
    # 1. Stwórz listę pięciu korutyn (NIE await-uj ich tutaj - chcemy mieć
    #    listę "obietnic", które jeszcze się nie zaczęły wykonywać):
    coros = ...  # --- Twój kod ---

    # 2. Uruchom je współbieżnie przez asyncio.gather i zbierz wyniki
    #    w jednej liście (gather rozpakowuje argumenty z gwiazdką: gather(*coros)):
    wyniki = ...  # --- Twój kod ---

    return wyniki


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START
print(f"\nWyniki: {wyniki}")
print(f"Łącznie: {elapsed:.2f}s")
```

## Spodziewany wynik

```
[t= 0.00s] START  page=0
[t= 0.00s] START  page=1
[t= 0.00s] START  page=2
[t= 0.00s] START  page=3
[t= 0.00s] START  page=4
[t= 1.00s] DONE   page=0
[t= 1.00s] DONE   page=1
[t= 1.00s] DONE   page=2
[t= 1.00s] DONE   page=3
[t= 1.00s] DONE   page=4

Wyniki: ['dane-0', 'dane-1', 'dane-2', 'dane-3', 'dane-4']
Łącznie: 1.01s
```

Porównaj z Demonstracją 2. Trzy istotne różnice:

* **Wszystkie pięć `START` pojawia się przy `t=0.00s`** - korutyny ruszają niemal jednocześnie.
* **Wszystkie pięć `DONE` pojawia się przy `t=1.00s`** - czekały **równolegle**, nie szeregowo. Czas oczekiwań **nie sumuje się**.
* **Łączny czas to ~1 s, nie 5 s.**

Co zaszło? `coros` to lista pięciu obiektów `coroutine` - żadna z nich jeszcze się nie wykonała (jak w Demonstracji 1). `asyncio.gather(*coros)` rejestruje je wszystkie w event loopie i czeka na zakończenie wszystkich. Event loop ma teraz pięć korutyn do nadzorowania - gdy pierwsza zawiesza się na `await asyncio.sleep(1)`, loop natychmiast rusza drugą, potem trzecią... wszystkie szybko zawisają na sleepach i czekają **równolegle**.

Wyniki w liście są **w tej samej kolejności**, w jakiej przekazaliśmy korutyny - niezależnie od tego, w jakiej kolejności faktycznie się zakończyły.

::: {.callout-note}
## Checkpoint
1. Czy wszystkie pięć printów `START` faktycznie pojawia się niemal w tej samej chwili (różnica < 0.01 s)?
2. Co zwraca `asyncio.gather(*coros)` - listę wyników, czy coś, na co trzeba dodatkowo zrobić `await`? (Spójrz: w `wyniki = ...` jest jeden `await`, czy dwa?)
3. Zmień zakres na `range(20)`. Czy łączny czas wciąż wynosi ~1 s? (Powinien, w granicach możliwości maszyny.)
4. Zmień `fetch_page` tak, by przyjmowała drugi argument `delay` i robiła `await asyncio.sleep(delay)`. Stwórz pięć korutyn z różnymi opóźnieniami (np. 1, 3, 2, 5, 4 s). W jakiej kolejności pojawiają się `DONE`? W jakiej kolejności są wyniki w liście?
:::

::: {.callout-tip}
## `gather(*coros)` vs `gather(coros)`
`asyncio.gather` przyjmuje korutyny **jako kolejne argumenty pozycyjne** (`gather(c1, c2, c3)`), nie jako listę. Jeśli masz listę, używasz operatora rozpakowywania: `gather(*coros)`. Pominięcie gwiazdki to częsty błąd - wtedy `gather` dostaje jeden argument typu `list`, którego nie umie obsłużyć.
:::

---

# Ćwiczenie 2: `create_task` - elementarny budulec

`gather` to wygodny skrót. Pod spodem jest mechanizm bardziej elementarny: rejestracja korutyny w event loopie **bez** czekania na nią. Służy do tego `asyncio.create_task`.

Utwórz plik `cw2.py`:

```python
import asyncio
import time

START = None


async def fetch_page(page_id):
    t0 = time.perf_counter() - START
    print(f"[t={t0:5.2f}s] START  page={page_id}")
    await asyncio.sleep(1)
    t1 = time.perf_counter() - START
    print(f"[t={t1:5.2f}s] DONE   page={page_id}")
    return f"dane-{page_id}"


async def main():
    # 1. Zarejestruj pięć korutyn jako task-i. To NIE czeka na zakończenie -
    #    create_task wraca natychmiast z obiektem Task:
    tasks = ...  # --- Twój kod ---

    # 2. Tu możemy wykonać dowolny inny kod synchroniczny.
    #    Task-i są już zarejestrowane w event loopie, ale zaczną się wykonywać
    #    dopiero przy najbliższym await poniżej:
    print(f"\n[w main] Tasks zarejestrowane, kontynuuję...\n")

    # 3. Teraz await na każdym task-u - zbieramy wyniki w kolejności rejestracji:
    wyniki = ...  # --- Twój kod ---

    return wyniki


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START
print(f"\nWyniki: {wyniki}")
print(f"Łącznie: {elapsed:.2f}s")
```

## Spodziewany wynik

```

[w main] Tasks zarejestrowane, kontynuuję...

[t= 0.00s] START  page=0
[t= 0.00s] START  page=1
[t= 0.00s] START  page=2
[t= 0.00s] START  page=3
[t= 0.00s] START  page=4
[t= 1.00s] DONE   page=0
[t= 1.00s] DONE   page=1
[t= 1.00s] DONE   page=2
[t= 1.00s] DONE   page=3
[t= 1.00s] DONE   page=4

Wyniki: ['dane-0', 'dane-1', 'dane-2', 'dane-3', 'dane-4']
Łącznie: 1.01s
```

Zwróć uwagę na **kolejność**:

* **`[w main] Tasks zarejestrowane`** pojawia się **PRZED** wszystkimi `START`. To dowód, że `create_task` zwraca natychmiast - `main` przeszedł przez pięć rejestracji bez ani jednego oddania sterowania, dotarł do printu, wykonał go, a dopiero **potem** (przy pierwszym `await`) event loop dostał szansę uruchomić zarejestrowane task-i.
* **Pięć `START` w jednej salwie, pięć `DONE` po sekundzie** - efekt dokładnie taki sam jak w Ćwiczeniu 1 z `gather`.
* **Łączny czas ~1 s** - identycznie jak `gather`.

Funkcjonalnie efekt jest ten sam co w `gather`. Różnica jest **strukturalna**: między rejestracją a oczekiwaniem mamy dziurę, w której można zrobić cokolwiek innego (zalogować postęp, zarejestrować dodatkowe task-i na podstawie warunków, wykonać lokalne obliczenia). `gather` tej dziury nie daje - rejestruje i czeka w jednym ruchu.

::: {.callout-tip}
## Kiedy `gather`, a kiedy `create_task`
* **`gather`** - domyślny wybór. Krótszy kod, jasna semantyka „uruchom te korutyny i daj mi wszystkie wyniki".
* **`create_task`** - gdy potrzebujesz fine-grained kontroli: rejestracja zadań w trakcie pracy programu (nie z góry), task-i „fire and forget" (rejestracja bez `await`), kombinacja `await` z timeoutem (`asyncio.wait_for(task, timeout=5)`).

W praktyce w tym kursie używamy `gather`. Pokazujemy `create_task`, żeby wiedzieć, że `gather` to skrót dla wzorca „create_task wszystkich + await wszystkich".
:::

::: {.callout-note}
## Checkpoint
1. Czy print `[w main] Tasks zarejestrowane` pojawia się **przed** czy **po** printach `START`? Co to mówi o tym, kiedy task-i zaczynają faktycznie biegnąć?
2. Co by się stało, gdybyś usunął całą sekcję `wyniki = [await t for t in tasks]` (lub jak to zapisałeś)? Spróbuj. (Wskazówka: `asyncio.run` zamknie event loop po zakończeniu `main`, a zarejestrowane task-i nie zdążą się wykonać - dostaniesz ostrzeżenie o anulowanych zadaniach.)
3. Czy potrafisz zapisać `wyniki` przez **list comprehension**, używając `await` wewnątrz? (To poprawna składnia: `[await t for t in tasks]`. `await` w comprehensji jest dozwolony tylko wewnątrz `async def`.)
:::

---

# Demonstracja 3: pułapka `time.sleep` w korutynie

Mamy wszystkie elementy współbieżności: `async def`, `await`, `gather` lub `create_task`. Czas pokazać, jak łatwo to zepsuć **jednym** złym wywołaniem.

Utwórz plik `demo3.py`:

```python
import asyncio
import time

START = None


async def fetch_page_zly(page_id):
    """ZŁY przykład: time.sleep zamiast asyncio.sleep wewnątrz korutyny."""
    t0 = time.perf_counter() - START
    print(f"[t={t0:5.2f}s] START  page={page_id}")
    time.sleep(1)  # <-- pułapka: blokuje event loop
    t1 = time.perf_counter() - START
    print(f"[t={t1:5.2f}s] DONE   page={page_id}")
    return f"dane-{page_id}"


async def main():
    coros = [fetch_page_zly(i) for i in range(5)]
    return await asyncio.gather(*coros)


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START
print(f"\nŁącznie: {elapsed:.2f}s")
```

Uruchom. Spodziewany wynik:

```
[t= 0.00s] START  page=0
[t= 1.00s] DONE   page=0
[t= 1.00s] START  page=1
[t= 2.00s] DONE   page=1
[t= 2.00s] START  page=2
[t= 3.00s] DONE   page=2
[t= 3.00s] START  page=3
[t= 4.00s] DONE   page=3
[t= 4.00s] START  page=4
[t= 5.00s] DONE   page=4

Łącznie: 5.01s
```

Wszystko jak w Ćwiczeniu 1 - `async def`, `await`, `gather` - ale **wynik dokładnie taki sam jak w pętli sekwencyjnej z Demonstracji 2**.

Dlaczego? `time.sleep(1)` jest funkcją **synchroniczną**. Nie zawiera żadnego `await`. Nie ma punktu zawieszenia. Z perspektywy event loopu wygląda to jak długie obliczenie, którego nie ma jak przerwać. Cały event loop **stoi** przez tę sekundę. Inne korutyny czekają na swoją kolej.

Dopóki któraś korutyna nie napotka prawdziwego `await` na czymś asynchronicznym (`asyncio.sleep`, `client.get`, `aiofiles.read`), event loop nie ma okazji przełączyć się na inną.

::: {.callout-warning}
## Reguła kciuka
W korutynie **nigdy nie wywołuj funkcji blokujących**. Każde czekanie na I/O musi być pod `await`, a wołana funkcja musi być napisana z myślą o asyncio.

| Synchronicznie (blokuje) | Asynchronicznie (`await`) |
|---|---|
| `time.sleep(1)` | `await asyncio.sleep(1)` |
| `requests.get(url)` | `await client.get(url)` (gdzie `client` to `httpx.AsyncClient`) |
| `open(path).read()` | `await aiofiles.open(path).read()` (poza zakresem kursu) |

Jeśli używasz biblioteki, która nie ma swojej wersji asynchronicznej - w korutynie **nie wolno** jej wywoływać bezpośrednio. Trzeba ją przerzucić do osobnego wątku przez `asyncio.to_thread` (też poza zakresem kursu).
:::

::: {.callout-note}
## Checkpoint
1. Czy printy `START` pojawiają się jednocześnie (jak w Ćwiczeniu 1) czy sekwencyjnie? Dlaczego - co technicznie blokuje event loop?
2. Spróbuj **dodać** `await asyncio.sleep(0)` tuż **po** `time.sleep(1)`. Czy coś się zmienia? (Nie - `time.sleep` już zablokowało sekundę, `asyncio.sleep(0)` po fakcie tylko oddaje sterowanie, ale szkoda już się stała.)
3. Spróbuj **zamienić** `time.sleep(1)` na `await asyncio.sleep(1)` (przywróć poprawną wersję). Wynik wraca do ~1 s - ale uwaga: zmiana to **dwa** elementy, nie jeden. Jakie?
:::

---

# Ćwiczenie 3: pierwszy async HTTP

Wszystko, co dotąd zrobiliśmy, działało na `asyncio.sleep` - symulowanym opóźnieniu w jednym procesie. Teraz pojadą prawdziwe żądania sieciowe do serwera Flask. Wzorzec pozostaje **identyczny** jak w Ćwiczeniu 1, podmieniamy tylko `asyncio.sleep` na `client.get`.

## Krok 0: serwer

W folderze `lab9/` utwórz plik `app.py` (skopiuj poniższy kod):

```python
# app.py - serwer dla Lab 9 i Lab 10
import time

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/data/<int:page>")
def data(page):
    time.sleep(1)  # symulacja wolnego serwera
    return jsonify({
        "page": page,
        "items": [f"item-{page}-{i}" for i in range(5)],
    })
```

Uruchom serwer w **Terminalu 1** (otwartym w `lab9/`):

```bash
flask run --debug -p 5000
```

Pozostaw go uruchomionego do końca labu.

::: {.callout-note}
## Sanity check
W **Terminalu 2** sprawdź serwer:

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/data/0
```

Pierwsze żądanie wraca natychmiast, drugie po sekundzie. To jest celowe - `/data/<page>` symuluje wolny endpoint, na którym chcemy zaobserwować przyspieszenie z async.
:::

::: {.callout-tip}
## Dlaczego `127.0.0.1`, nie `localhost`
Na Windowsie `requests` (i przeglądarka) próbuje najpierw IPv6, dostaje odmowę, dopiero potem przechodzi na IPv4 - co dorzuca ~2 s na każdym żądaniu. `127.0.0.1` ten problem omija. W całym kursie używamy formy z adresem IP.
:::

## Krok A: klient sync

Utwórz plik `cw3_sync.py`:

```python
import time

import requests

BASE = "http://127.0.0.1:5000"
START = time.perf_counter()


def fetch_page(page):
    t0 = time.perf_counter() - START
    print(f"[t={t0:5.2f}s] START  page={page}")
    r = requests.get(f"{BASE}/data/{page}")
    r.raise_for_status()
    t1 = time.perf_counter() - START
    print(f"[t={t1:5.2f}s] DONE   page={page}")
    return r.json()


wyniki = [fetch_page(p) for p in range(10)]

elapsed = time.perf_counter() - START
print(f"\nPobrano {len(wyniki)} stron w {elapsed:.2f}s")
```

Uruchom. Spodziewany wynik:

```
[t= 0.00s] START  page=0
[t= 1.01s] DONE   page=0
[t= 1.01s] START  page=1
[t= 2.02s] DONE   page=1
[t= 2.02s] START  page=2
[t= 3.03s] DONE   page=2
...
[t= 9.09s] START  page=9
[t=10.10s] DONE   page=9

Pobrano 10 stron w 10.10s
```

Przeplot jest dokładnie taki sam jak w Demonstracji 2 - `START 0 → DONE 0 → START 1 → DONE 1 → ...`. Zamiast `asyncio.sleep` mamy realną sieć i serwer Flask, ale obraz przepływu jest identyczny: każde żądanie startuje **dopiero po zakończeniu poprzedniego**, czasy się **sumują**.

## Krok B: klient async

Utwórz plik `cw3_async.py`:

```python
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:5000"
START = None


async def fetch_page(client, page):
    t0 = time.perf_counter() - START
    print(f"[t={t0:5.2f}s] START  page={page}")
    # 1. Wykonaj asynchroniczne żądanie GET na adres f"{BASE}/data/{page}":
    r = ...  # --- Twój kod ---
    r.raise_for_status()
    t1 = time.perf_counter() - START
    print(f"[t={t1:5.2f}s] DONE   page={page}")
    return r.json()


async def main():
    # 2. Otwórz blok async with z klientem httpx.AsyncClient() jako client:
    # --- Twój kod ---
        # 3. Stwórz listę dziesięciu korutyn fetch_page(client, p) i odpal je
        #    współbieżnie przez asyncio.gather, zwróć listę wyników:
        coros = ...  # --- Twój kod ---
        return ...  # --- Twój kod ---


START = time.perf_counter()
wyniki = asyncio.run(main())
elapsed = time.perf_counter() - START
print(f"\nPobrano {len(wyniki)} stron w {elapsed:.2f}s")
```

Wskazówki: konstrukcje, których użyjesz, widziałeś już w `demo*.py`, `cw1.py`, `cw2.py`. Nowość to dwie linijki: `async with httpx.AsyncClient() as client` i `await client.get(...)`. Reszta to ten sam wzorzec, co w Ćwiczeniu 1.

## Spodziewany wynik

```
[t= 0.00s] START  page=0
[t= 0.01s] START  page=1
[t= 0.01s] START  page=2
[t= 0.01s] START  page=3
[t= 0.01s] START  page=4
[t= 0.01s] START  page=5
[t= 0.01s] START  page=6
[t= 0.02s] START  page=7
[t= 0.02s] START  page=8
[t= 0.02s] START  page=9
[t= 1.04s] DONE   page=0
[t= 1.04s] DONE   page=1
[t= 1.05s] DONE   page=2
[t= 1.05s] DONE   page=3
[t= 1.05s] DONE   page=4
[t= 1.06s] DONE   page=5
[t= 1.06s] DONE   page=6
[t= 1.06s] DONE   page=7
[t= 1.07s] DONE   page=8
[t= 1.07s] DONE   page=9

Pobrano 10 stron w 1.07s
```

Ten sam serwer, te same dane, ten sam pakiet sieciowy w środku - i ~10× szybciej.

Sam końcowy timer (10 s vs 1 s) jest mocny, ale **przeplot jest tym, co dydaktycznie się liczy**:

* **Wszystkie dziesięć `START` pojawia się w pierwszych ~10 ms.** Klient asynchroniczny wysłał wszystkie żądania niemal jednocześnie, każde po wysłaniu oddało sterowanie event loopowi.
* **Wszystkie dziesięć `DONE` pojawia się w drugiej sekundzie.** Serwer Flask obsłużył je równolegle, klient odebrał wszystkie odpowiedzi w bliskich odstępach.
* **Brak przeplotu `START → DONE → START → DONE`** - to jest wizualna sygnatura współbieżności.

Dwa nowe elementy w kodzie, które zobaczyłeś w Kroku B:

* **`async with httpx.AsyncClient() as client`** - blok zarządzania zasobem. `httpx.AsyncClient` trzyma pulę połączeń TCP do serwera; `async with` gwarantuje, że pula zostanie zamknięta po wyjściu z bloku. Analogicznie do `with open(...)` przy plikach. Bez tego dostaniesz `ResourceWarning: unclosed connector`.
* **`await client.get(url)`** - punkt zawieszenia. To jest moment, w którym event loop może przełączyć się na inną korutynę. Reszta API (`r.status_code`, `r.json()`, `r.text`, `r.raise_for_status()`) działa **dokładnie tak samo** jak w `requests` - to jest celowy projekt `httpx`.

::: {.callout-warning}
## Antywzorzec: `requests.get` wewnątrz `async def`
Kuszące jest „opakować" znane wywołania `requests` w `async def`:

```python
async def fetch_page_zly(page):
    r = requests.get(f"{BASE}/data/{page}")  # <-- pułapka
    return r.json()
```

Składnia jest poprawna - Python nie zaprotestuje. Ale efekt będzie identyczny jak Demonstracja 3 z `time.sleep`: pętla po `await` zwraca ~10 s, nie ~1 s. Powód jest ten sam: `requests.get` jest synchroniczne i blokuje event loop tak samo, jak `time.sleep`.

To jest druga twarz tego samego błędu. Reguła pozostaje: w korutynie wszystko, co czeka na I/O, musi być wykonane przez `await` na bibliotece **napisanej z myślą o asyncio** (`httpx`, `aiofiles`, `asyncpg` itd.).

Jeśli masz czas, sprawdź to sam - skopiuj `cw3_async.py` jako `cw3_pulapka.py`, podmień `httpx.AsyncClient` na bezpośrednie wywołania `requests.get` i porównaj timery.
:::

::: {.callout-tip}
## Dlaczego serwer Flask z `time.sleep` w ogóle się skaluje
Flask uruchomiony przez `flask run` domyślnie obsługuje żądania **wielowątkowo** - każde przychodzące żądanie dostaje swój wątek roboczy. `time.sleep(1)` w endpoincie blokuje **tylko ten jeden wątek** - inne wątki są wolne i mogą obsłużyć kolejne żądania.

Dlatego nasz klient async może wysłać 10 żądań naraz i serwer obsłuży je równolegle - każde we własnym wątku, w którym `time.sleep` rozdziela się niezależnie.

Asynchroniczność klienta i wielowątkowość serwera to **dwa osobne wymiary**. W tym labie klient jest async, a serwer wielowątkowy - i to wystarcza do współbieżności. W Lab 10 wrócimy do tego, gdy pojawi się problem „za dużo żądań naraz".
:::

::: {.callout-note}
## Checkpoint
1. Czy w wyjściu `cw3_async.py` **wszystkie** `START` pojawiają się przed **pierwszym** `DONE`? To jest wizualna sygnatura współbieżności - bez tego coś nie działa.
2. Zmień zakres na `range(20)`. Czy łączny czas wciąż jest bliski 1 s? Co przy `range(50)`? (Pojawiają się pierwsze efekty skali - to temat Lab 10.)
3. Czy struktura danych w `wyniki` jest tej samej postaci, co w wersji sync? (Tak - `r.json()` zwraca słownik o tej samej zawartości; klient inny, dane te same.)
4. Co się stanie, gdy usuniesz `async with` i zrobisz `client = httpx.AsyncClient()` bez bloku, a na końcu `main()` nie wywołasz `await client.aclose()`? Spróbuj. (Działa, ale Python wypisze ostrzeżenie o niezamkniętych zasobach. To samo, co `with open(...)` przy plikach - dobra praktyka.)
:::

---

# Podsumowanie

W tym labie:

* zobaczyłeś, że korutyna to **obietnica wykonania** - wywołanie `fetch_page(0)` bez `await` zwraca obiekt typu `coroutine`, ale ciało funkcji się nie uruchamia,
* zauważyłeś, że pętla `for ... await ...` jest **sekwencyjna** - sam `await` niczego nie przyspiesza, jeśli nie ma „innego" zadania, na które event loop mógłby się przełączyć,
* opanowałeś `asyncio.gather` jako podstawowy mechanizm współbieżności - rejestruje wiele korutyn naraz i czeka na wszystkie; wyniki w kolejności wejściowej,
* poznałeś `asyncio.create_task` jako bardziej elementarną konstrukcję - rejestracja bez czekania, z dziurą na inny kod między rejestracją a `await`,
* zdiagnozowałeś pułapkę `time.sleep` w korutynie - synchroniczne wywołanie blokuje event loop tak samo, jak każda inna funkcja synchroniczna, niwecząc współbieżność,
* napisałeś pierwszego klienta async HTTP z `httpx.AsyncClient` i porównałeś go z `requests` na tym samym zadaniu - 10 stron, ~10 s vs ~1 s, ten sam serwer,
* zobaczyłeś, że antywzorzec `requests.get` w `async def` jest **tą samą** pułapką co `time.sleep` w korutynie - dwa różne objawy jednej zasady.

**Co dalej:**

* **Lab 10**: async HTTP w praktyce. Co, gdy mamy nie 10, a 1000 URL-i? Pojawia się problem przeciążenia (klienta, serwera, sieci) i potrzeba ograniczania współbieżności. Poznasz `asyncio.Semaphore` (domyślny mechanizm „grzeczności" w async), `as_completed` (przetwarzanie wyników w miarę kończenia), `return_exceptions=True` (jak `gather` radzi sobie z wyjątkami) i timeouty. Pełen pipeline: pobranie → walidacja → zapis. Serwer (`app.py` z dzisiaj) rozszerzymy o endpointy z różnymi opóźnieniami i o endpointy, które czasem rzucają błędy.