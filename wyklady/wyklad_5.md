---
title: "Wykład 5: Asynchroniczność w Pythonie — od intuicji do httpx"
subtitle: "Automatyczne pozyskiwanie danych"
author: "Tomasz Rodak"
toc-title: "Spis treści"
---

## Cele i zakres

Na poprzednich wykładach i labach pobieraliśmy dane z sieci synchronicznie: jedno żądanie za drugim, w pętli `for`. To podejście jest proste i wystarczające, gdy żądań jest kilka. Przy dziesiątkach lub setkach żądań staje się jednak nieakceptowalnie wolne — nie dlatego, że procesor jest przeciążony, lecz dlatego, że klient przez większość czasu **bezczynnie czeka** na odpowiedzi serwera.

Zakres obejmuje:

* problem synchronicznego pobierania — diagnoza i pomiar,
* I/O-bound vs CPU-bound — dlaczego standardowe techniki przyspieszania (szybszy procesor, lepszy algorytm) tu nie pomagają,
* model asynchroniczny — event loop, korutyny, `await`,
* `asyncio` od podstaw — `async def`, `asyncio.sleep()`, `asyncio.run()`,
* współbieżność — `create_task`, `gather`, `as_completed`,
* `httpx.AsyncClient` — asynchroniczny HTTP z API w stylu `requests`,
* kontrola i odporność — `Semaphore`, timeouty, obsługa błędów w `gather`.

---

## Problem: synchroniczna pętla

### Scenariusz

Wyobraźmy sobie serwer Flask z endpointem, który odpowiada z jednosekundowym opóźnieniem — symuluje np. bazę danych, obliczenia lub wolne łącze:

```python
import time
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/data/<int:page>")
def data(page):
    time.sleep(1)  # symulacja wolnego serwera
    return jsonify({"page": page, "items": [f"item-{page}-{i}" for i in range(5)]})
```

Klient w `requests`, który pobiera 10 stron:

```python
import requests
import time

start = time.perf_counter()

results = []
for page in range(10):
    r = requests.get(f"http://127.0.0.1:5000/data/{page}")
    results.append(r.json())

elapsed = time.perf_counter() - start
print(f"Pobrano {len(results)} stron w {elapsed:.1f}s")
# Pobrano 10 stron w 10.2s
```

Dziesięć stron, po sekundzie każda — łącznie ponad 10 sekund.

### Diagnoza

Problem nie leży w procesorze. Procesor praktycznie nic nie robi — parsowanie JSON z jednej strony trwa ułamki milisekundy. Problem leży w **oczekiwaniu na I/O**: klient wysyła żądanie, potem stoi bezczynnie, aż serwer odpowie. Dopiero wtedy wysyła kolejne żądanie.

```
Żądanie 0:  [====wysyłka====][.........czekanie.........][odbiór]
Żądanie 1:                                                       [====wysyłka====][.........czekanie.........][odbiór]
Żądanie 2:                                                                                                           [====wysyłka====]...
```

Każde żądanie zaczyna się **dopiero po zakończeniu poprzedniego**. Okresy bezczynnego czekania sumują się.

### I/O-bound vs CPU-bound

To rozróżnienie jest fundamentalne:

* **CPU-bound** — program jest wolny, bo procesor ma dużo do obliczenia (np. trenowanie modelu ML, kompresja wideo). Rozwiązanie: szybszy procesor, lepszy algorytm, wielowątkowość.
* **I/O-bound** — program jest wolny, bo czeka na operacje wejścia/wyjścia (sieć, dysk, baza danych). Procesor jest bezczynny przez większość czasu.

Pobieranie danych z sieci to klasyczny problem I/O-bound. Szybszy procesor nic tu nie zmieni — i tak 99% czasu to oczekiwanie na odpowiedź serwera.

Rozwiązanie: zamiast czekać bezczynnie na jedno żądanie, **wyślij kolejne żądania w międzyczasie**. To jest idea asynchroniczności.

---

## Analogia: kelner w restauracji

### Kelner synchroniczny

Wyobraź sobie kelnera, który obsługuje restaurację w ten sposób:

1. Podchodzi do stolika 1, przyjmuje zamówienie.
2. Idzie do kuchni, przekazuje zamówienie.
3. **Stoi przy okienku i czeka**, aż danie będzie gotowe.
4. Odbiera danie, niesie do stolika 1.
5. Dopiero teraz podchodzi do stolika 2.

Jeśli kuchnia potrzebuje 10 minut na danie, a w restauracji jest 5 stolików — ostatni klient czeka 50 minut. Kelner przez większość czasu **stoi bezczynnie** przy okienku.

### Kelner asynchroniczny

Ten sam kelner, ale zmienia strategię:

1. Podchodzi do stolika 1, przyjmuje zamówienie, przekazuje do kuchni.
2. **Nie czeka** — wraca na salę.
3. Podchodzi do stolika 2, przyjmuje zamówienie, przekazuje do kuchni.
4. Podchodzi do stolika 3...
5. Kuchnia sygnalizuje: „danie dla stolika 1 gotowe" — kelner odbiera i podaje.

Jeden kelner, te same dania, ten sam czas przygotowania — ale wszystkie stoliki złożyły zamówienia niemal jednocześnie. Łączny czas obsługi to czas najdłuższego dania, nie suma wszystkich.

### Mapowanie na programowanie

| Restauracja | Programowanie |
|---|---|
| kelner | event loop |
| zamówienie | żądanie HTTP |
| kuchnia | serwer |
| gotowe danie | odpowiedź |
| „stoi i czeka" | `requests.get()` — blokuje |
| „wraca na salę" | `await` — oddaje sterowanie |

Kluczowy wniosek: nie potrzebujemy wielu kelnerów (wątków, procesów). Potrzebujemy **jednego kelnera**, który nie blokuje się na oczekiwaniu.

---

## `asyncio` od podstaw

### Korutyna: funkcja, którą można zawieszać

W zwykłym Pythonie wywołanie funkcji blokuje — program czeka na jej zakończenie:

```python
def fetch_page(page_id):
    time.sleep(1)       # tu program stoi
    return f"dane-{page_id}"

result = fetch_page(1)  # wraca po 1 sekundzie
```

**Korutyna** (coroutine) to funkcja, której wykonanie można **zawiesić** w punkcie oczekiwania i wznowić później. Definiujemy ją słowem `async def`:

```python
import asyncio

async def fetch_page(page_id):
    print(f"Start: strona {page_id}")
    await asyncio.sleep(1)   # zawieszenie — oddajemy sterowanie
    print(f"Gotowe: strona {page_id}")
    return f"dane-{page_id}"
```

Trzy nowe elementy:

* `async def` — deklaruje korutynę (zamiast zwykłej funkcji).
* `await` — punkt zawieszenia. Mówi: „tu czekam na wynik, ale w międzyczasie event loop może robić coś innego".
* `asyncio.sleep(1)` — asynchroniczny odpowiednik `time.sleep(1)`. Nie blokuje event loopu — tylko rejestruje „obudź mnie za sekundę".

### `asyncio.run()` — uruchomienie event loopu

Korutyny nie można wywołać jak zwykłej funkcji. Potrzebny jest **event loop** — pętla sterująca, która zarządza zawieszaniem i wznawianiem korutyn:

```python
async def main():
    result = await fetch_page(1)
    print(result)

asyncio.run(main())
```

```
Start: strona 1
Gotowe: strona 1
dane-1
```

`asyncio.run()` tworzy event loop, uruchamia w nim korutynę `main()` i czeka na jej zakończenie. To jedyny punkt wejścia — cały kod asynchroniczny żyje wewnątrz `asyncio.run()`.

Na razie nie ma żadnego zysku — jedna korutyna działa tak samo jak zwykła funkcja. Zysk pojawia się, gdy uruchomimy **wiele korutyn jednocześnie**.

---

## Współbieżność: `create_task` i `gather`

### `asyncio.create_task()` — rejestracja bez czekania

`create_task` rejestruje korutynę w event loopie i **natychmiast wraca** — nie czeka na jej zakończenie:

```python
async def main():
    task1 = asyncio.create_task(fetch_page(1))
    task2 = asyncio.create_task(fetch_page(2))
    
    # Obie korutyny już działają w tle.
    # Teraz czekamy na wyniki:
    result1 = await task1
    result2 = await task2
    
    print(result1, result2)

asyncio.run(main())
```

```
Start: strona 1
Start: strona 2
Gotowe: strona 1
Gotowe: strona 2
dane-1 dane-2
```

Obie korutyny wystartowały niemal jednocześnie. Każda czeka sekundę, ale czekają **równolegle** — łączny czas to ~1 sekunda, nie 2.

### `asyncio.gather()` — czekaj na wszystkie

Gdy mamy wiele zadań, `gather` jest wygodniejszy niż ręczne `create_task` + `await` dla każdego:

```python
async def main():
    tasks = [fetch_page(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    print(results)

asyncio.run(main())
```

```
Start: strona 0
Start: strona 1
Start: strona 2
Start: strona 3
Start: strona 4
Gotowe: strona 0
Gotowe: strona 1
Gotowe: strona 2
Gotowe: strona 3
Gotowe: strona 4
['dane-0', 'dane-1', 'dane-2', 'dane-3', 'dane-4']
```

Pięć korutyn, każda czeka sekundę — łączny czas to ~1 sekunda. `gather` zwraca listę wyników **w tej samej kolejności**, w jakiej przekazaliśmy korutyny.

### `asyncio.as_completed()` — wyniki w kolejności kończenia

`gather` czeka, aż **wszystkie** korutyny się zakończą, i dopiero wtedy zwraca wyniki. Czasem chcemy przetwarzać wyniki **w miarę jak się pojawiają** — np. wyświetlać postęp lub zapisywać dane na bieżąco.

`as_completed` zwraca iterator korutyn do oczekiwania — w kolejności, w jakiej się kończą:

```python
async def fetch_page_variable(page_id, delay):
    """Strony z różnymi czasami odpowiedzi."""
    print(f"Start: strona {page_id} (delay={delay}s)")
    await asyncio.sleep(delay)
    return f"dane-{page_id}"

async def main():
    tasks = [
        fetch_page_variable(0, 3.0),
        fetch_page_variable(1, 1.0),
        fetch_page_variable(2, 2.0),
    ]
    
    for coro in asyncio.as_completed(tasks):
        result = await coro
        print(f"Otrzymano: {result}")

asyncio.run(main())
```

```
Start: strona 0 (delay=3.0s)
Start: strona 1 (delay=1.0s)
Start: strona 2 (delay=2.0s)
Otrzymano: dane-1
Otrzymano: dane-2
Otrzymano: dane-0
```

Strona 1 skończyła się pierwsza (najkrótsze opóźnienie), mimo że została przekazana jako druga. `as_completed` pozwala reagować natychmiast, bez czekania na najwolniejsze zadanie.

### `gather` vs `as_completed` — kiedy co

| Cecha | `gather` | `as_completed` |
|---|---|---|
| Zwraca wyniki | po zakończeniu wszystkich | w kolejności kończenia |
| Kolejność wyników | taka sama jak wejściowa | kolejność zakończenia |
| Zastosowanie | pobranie stałego zestawu danych | przetwarzanie na bieżąco, postęp |

W praktyce `gather` jest częstszy — prostszy kod, przewidywalna kolejność. `as_completed` przydaje się, gdy chcemy np. wyświetlać pasek postępu lub zapisywać wyniki do pliku na bieżąco.

---

## Od `asyncio.sleep` do prawdziwego HTTP: `httpx`

### Dlaczego nie `requests`

Do tej pory używaliśmy `asyncio.sleep` jako symulacji operacji I/O. W prawdziwym kodzie chcemy wysyłać żądania HTTP. Czy można użyć `requests`?

```python
async def fetch(url):
    r = requests.get(url)      # TO NIE DZIAŁA jak chcemy
    return r.text
```

Ten kod jest poprawny składniowo, ale **nie daje żadnego zysku z asynchroniczności**. `requests.get()` jest funkcją synchroniczną — blokuje event loop na czas oczekiwania na odpowiedź. Inne korutyny nie mogą działać w międzyczasie. Efekt: taki sam jak zwykła pętla `for`.

Problem: `requests.get()` nie jest korutyną — nie można na niej zrobić `await`, bo nie ma punktu zawieszenia. Event loop nie wie, kiedy `requests.get()` czeka na sieć, a kiedy przetwarza dane — z jego perspektywy to jedna nieprzerwana operacja.

### `httpx` — asynchroniczny klient HTTP

`httpx` to biblioteka HTTP, która ma API niemal identyczne z `requests`, ale wspiera natywny tryb asynchroniczny. To, co student zna z `requests` — `r.status_code`, `r.text`, `r.json()`, `r.headers` — działa tak samo w `httpx`.

Instalacja:

```bash
pip install httpx
```

Porównanie:

```python
# requests (synchroniczne)
import requests

r = requests.get("http://127.0.0.1:5000/data/1")
print(r.json())
```

```python
# httpx (asynchroniczne)
import httpx

async def fetch():
    async with httpx.AsyncClient() as client:
        r = await client.get("http://127.0.0.1:5000/data/1")
        print(r.json())

asyncio.run(fetch())
```

Dwie różnice:

1. `httpx.AsyncClient()` zamiast `requests` — i używamy go w bloku `async with`.
2. `await client.get(...)` zamiast `requests.get(...)` — tu jest punkt zawieszenia.

### Dlaczego `async with`

`httpx.AsyncClient` zarządza **pulą połączeń** TCP. Blok `async with` gwarantuje, że połączenia zostaną zamknięte po zakończeniu pracy — analogicznie do `with open(...)` przy plikach. Bez `async with` połączenia mogą wyciekać, a program wypisywać ostrzeżenia.

### Pełny przykład: sync vs async

Serwer Flask z opóźnieniem (ten sam co wcześniej):

```python
# serwer.py
import time
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/data/<int:page>")
def data(page):
    time.sleep(1)
    return jsonify({"page": page, "items": [f"item-{page}-{i}" for i in range(5)]})
```

Klient synchroniczny:

```python
import requests
import time

start = time.perf_counter()

results = []
for page in range(10):
    r = requests.get(f"http://127.0.0.1:5000/data/{page}")
    results.append(r.json())

elapsed = time.perf_counter() - start
print(f"Sync: {len(results)} stron w {elapsed:.1f}s")
# Sync: 10 stron w 10.2s
```

Klient asynchroniczny:

```python
import asyncio
import httpx
import time

async def main():
    start = time.perf_counter()
    
    async with httpx.AsyncClient() as client:
        tasks = [client.get(f"http://127.0.0.1:5000/data/{page}") for page in range(10)]
        responses = await asyncio.gather(*tasks)
    
    results = [r.json() for r in responses]
    
    elapsed = time.perf_counter() - start
    print(f"Async: {len(results)} stron w {elapsed:.1f}s")

asyncio.run(main())
# Async: 10 stron w 1.3s
```

Wynik: ~10x szybciej. Wszystkie żądania wysłane niemal jednocześnie, klient czekał na odpowiedzi równolegle.

---

## Kontrola współbieżności

### Problem: za dużo żądań naraz

W przykładzie wyżej wysłaliśmy 10 żądań jednocześnie. Co, jeśli mamy 1000 URL-ów?

```python
tasks = [client.get(url) for url in urls]  # 1000 żądań naraz
responses = await asyncio.gather(*tasks)
```

To może spowodować:

* **przeciążenie serwera** — 1000 jednoczesnych połączeń to de facto atak DDoS,
* **wyczerpanie pamięci** — 1000 otwartych połączeń i buforów,
* **błędy sieciowe** — system operacyjny ma limit otwartych gniazd.

Potrzebujemy mechanizmu, który ograniczy liczbę **równoczesnych** żądań — np. do 5 lub 10.

### `asyncio.Semaphore` — ogranicznik współbieżności

Semafor to licznik, który pozwala najwyżej N korutynom wejść do chronionej sekcji jednocześnie. Pozostałe czekają, aż któraś wyjdzie:

```python
sem = asyncio.Semaphore(5)  # maks. 5 jednocześnie

async def fetch_limited(client, url):
    async with sem:                         # czekaj na wolne miejsce
        r = await client.get(url)           # wykonaj żądanie
        return r.json()                     # po return — miejsce się zwalnia

async def main():
    urls = [f"http://127.0.0.1:5000/data/{i}" for i in range(50)]
    
    async with httpx.AsyncClient() as client:
        tasks = [fetch_limited(client, url) for url in urls]
        results = await asyncio.gather(*tasks)
    
    print(f"Pobrano {len(results)} stron")

asyncio.run(main())
```

Bez semafora: 50 żądań jednocześnie. Z semaforem (5): w dowolnym momencie działa najwyżej 5 żądań, pozostałe czekają na zwolnienie miejsca.

Analogia: 5 okienek w urzędzie. W poczekalni może być 100 osób, ale obsługiwanych jest jednocześnie najwyżej 5. Gdy ktoś odchodzi od okienka, następna osoba podchodzi.

### Timeouty

`httpx` wspiera timeouty na dwóch poziomach:

```python
# Timeout domyślny dla wszystkich żądań w kliencie
async with httpx.AsyncClient(timeout=10.0) as client:
    r = await client.get(url)

# Timeout per żądanie (nadpisuje domyślny)
r = await client.get(url, timeout=5.0)
```

Timeout dotyczy **całego żądania** — od wysłania do otrzymania pełnej odpowiedzi. Jeśli serwer nie odpowie w zadanym czasie, `httpx` rzuca `httpx.TimeoutException`.

W kontekście asynchronicznym timeout jest szczególnie ważny: jedno wiszące żądanie może blokować miejsce w semaforze, opóźniając wszystkie pozostałe.

---

## Obsługa błędów w `gather`

### Domyślne zachowanie: przerwanie na pierwszym błędzie

Domyślnie `gather` przerywa działanie, gdy którakolwiek korutyna rzuci wyjątek — i propaguje ten wyjątek do kodu wywołującego:

```python
async def fetch_page(client, url):
    r = await client.get(url)
    r.raise_for_status()
    return r.json()

async def main():
    urls = [
        "http://127.0.0.1:5000/data/1",
        "http://127.0.0.1:5000/nie-istnieje",   # 404
        "http://127.0.0.1:5000/data/3",
    ]
    async with httpx.AsyncClient() as client:
        tasks = [fetch_page(client, url) for url in urls]
        try:
            results = await asyncio.gather(*tasks)
        except httpx.HTTPStatusError as e:
            print(f"Błąd: {e}")
            # Nie wiemy, które żądania się udały, a które nie
```

Problem: dostajemy jeden wyjątek, ale nie wiemy, ile żądań się udało i jakie są ich wyniki.

### `return_exceptions=True` — zbierz wszystko

Parametr `return_exceptions=True` zmienia zachowanie: `gather` nie przerywa na wyjątkach, ale wstawia je do listy wyników na odpowiadające pozycje:

```python
async def main():
    urls = [
        "http://127.0.0.1:5000/data/1",
        "http://127.0.0.1:5000/nie-istnieje",   # 404
        "http://127.0.0.1:5000/data/3",
    ]
    async with httpx.AsyncClient() as client:
        tasks = [fetch_page(client, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            print(f"BŁĄD  {url} → {result}")
        else:
            print(f"OK    {url} → {len(result['items'])} elementów")

asyncio.run(main())
```

```
OK    http://127.0.0.1:5000/data/1 → 5 elementów
BŁĄD  http://127.0.0.1:5000/nie-istnieje → ...
OK    http://127.0.0.1:5000/data/3 → 5 elementów
```

Wyniki: 2 sukcesy, 1 błąd — ale żaden wynik nie jest utracony.

### Alternatywa: `try/except` wewnątrz korutyny

Zamiast filtrować wyniki po `gather`, można obsłużyć błędy **wewnątrz** każdej korutyny:

```python
async def fetch_page_safe(client, url):
    try:
        r = await client.get(url, timeout=5.0)
        r.raise_for_status()
        return {"url": url, "status": "ok", "data": r.json()}
    except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
        return {"url": url, "status": "error", "error": str(e)}
```

Teraz `gather` nigdy nie otrzyma wyjątku — każda korutyna zwraca słownik z wynikiem lub opisem błędu. Nie trzeba `return_exceptions=True`.

Oba podejścia są poprawne. `return_exceptions=True` jest prostsze przy jednorazowym przetwarzaniu wyników. `try/except` w korutynie daje więcej kontroli — np. pozwala na logowanie błędów w miejscu ich wystąpienia lub na retry wewnątrz korutyny.

---

## `time.sleep` vs `asyncio.sleep` — pułapka blokowania

Jedna z najczęstszych pomyłek przy nauce asynchroniczności: użycie `time.sleep` zamiast `asyncio.sleep` wewnątrz korutyny.

```python
async def bad_fetch(page_id):
    time.sleep(1)         # BLOKUJE event loop!
    return f"dane-{page_id}"

async def main():
    tasks = [bad_fetch(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

asyncio.run(main())
# Czas: ~5 sekund — brak współbieżności!
```

`time.sleep(1)` jest operacją synchroniczną — blokuje **cały event loop** na sekundę. Inne korutyny nie mogą działać w tym czasie. Efekt: 5 korutyn wykonuje się sekwencyjnie, jakby nie było żadnego `async`.

Reguła: wewnątrz korutyny **nigdy nie używaj funkcji blokujących** (`time.sleep`, `requests.get`, `open().read()` na dużym pliku). Używaj ich asynchronicznych odpowiedników (`asyncio.sleep`, `httpx.AsyncClient`, `aiofiles`).

To samo dotyczy serwera Flask użytego w naszych przykładach: `time.sleep(1)` w endpoincie Flask **celowo** symuluje wolny serwer. To nie jest kod asynchroniczny — Flask jest synchroniczny i obsługuje po jednym żądaniu na wątek. Asynchroniczny jest **klient** (`httpx`), który nie czeka na odpowiedź jednego żądania, zanim wyśle następne.

---

## Podsumowanie

Na tym wykładzie:

* zdiagnozowaliśmy problem synchronicznego pobierania — klient bezczynnie czeka na każdą odpowiedź, a czasy oczekiwania się sumują,
* rozróżniliśmy I/O-bound od CPU-bound — pobieranie danych z sieci to klasyczny I/O-bound, gdzie procesor jest bezczynny,
* poznaliśmy model event loop na analogii kelnera — jeden kelner (event loop) obsługuje wiele stolików (żądań), nie blokując się na oczekiwaniu,
* nauczyliśmy się składni `async def` / `await` / `asyncio.run()` — korutyna to funkcja, którą można zawieszać w punktach `await`,
* zobaczyliśmy `gather` (czekaj na wszystkie, wyniki w kolejności wejściowej) i `as_completed` (wyniki w kolejności kończenia),
* przeszliśmy od symulacji (`asyncio.sleep`) do prawdziwego HTTP z `httpx.AsyncClient` — API identyczne z `requests`, z dodanym `await`,
* poznaliśmy `Semaphore` jako ogranicznik współbieżności i `return_exceptions=True` jako mechanizm zbierania błędów bez przerywania.

**Co dalej:**

* **Lab 9**: ćwiczenia prowadzone — od `asyncio.sleep` (suche symulacje, wizualizacja kolejności wykonania) przez `create_task` / `gather` do pierwszych żądań async HTTP do lokalnego serwera Flask z opóźnieniami. Porównanie sync vs async na tym samym zadaniu.
* **Lab 10**: async HTTP w praktyce — serwer z wieloma endpointami i sztucznymi opóźnieniami, `httpx.AsyncClient` + `gather`, `Semaphore`, `as_completed`, obsługa błędów. Pełny pipeline: pobranie, przetworzenie, zapis.