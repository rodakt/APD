---
title: "Lab 0: Python — podstawy"
subtitle: "Automatyczne pozyskiwanie danych — ćwiczenia"
author: "Tomasz Rodak"
---


# Cel

Zakres materiału:

* Poruszanie się po zagnieżdżonych słownikach i listach (struktury danych spotykane w odpowiedziach JSON),
* Pisanie funkcji z parametrami domyślnymi,
* Obsługa wyjątków (`try` / `except`),
* Praca z plikami i katalogami (`pathlib`, `json`),
* Sterowanie przepływem: pętla `for`, `while` z `break`, f-stringi.

Narzędzia: Python 3, Thonny.

---

# Przygotowanie środowiska

## Thonny

Na dzisiejszych zajęciach korzystamy z **Thonny** — lekkiego edytora Pythona z wbudowanym interpreterem, oknem zmiennych i debuggerem. Thonny nie podpowiada kodu automatycznie, co jest zaletą na etapie powtórki — zmusza do samodzielnego pisania.

Otwórz Thonny. Upewnij się, że w prawym dolnym rogu widoczna jest wersja Pythona **3.10** lub nowsza. Jeśli nie — zgłoś.

W Thonnym będziemy pracować w dwóch trybach:

* **Edytor** (górny panel) — tu piszesz skrypty i uruchamiasz je klawiszem **F5** (lub przyciskiem ▶).
* **Shell** (dolny panel) — tu widzisz wyniki i możesz wpisywać pojedyncze polecenia.

## Szybki test

Utwórz nowy plik (`File → New`), wpisz:

```python
import sys
print("Python", sys.version)
print("Wszystko działa!")
```

Zapisz plik jako `lab0_test.py` i uruchom (F5).

::: checkpoint
**Checkpoint:** Czy widzisz w Shellu wersję Pythona i komunikat „Wszystko działa!"? Jeśli nie — zgłoś, zanim przejdziesz dalej.
:::

## Instalacja pakietu

Na tym labie nie potrzebujemy zewnętrznych pakietów, ale przećwiczmy instalację — to umiejętność, która będzie potrzebna na kolejnych zajęciach.

W Thonnym: **Tools → Manage packages…**, wpisz `requests`, kliknij **Install**.

Sprawdź, czy instalacja się powiodła:

```python
import requests
print("requests", requests.__version__)
```

Jeśli widzisz wersję (np. `2.31.0`) — gotowe. Jeśli `ModuleNotFoundError` — wróć do Manage packages.

::: key-concept
**Instalacja pakietów — powtarzalna czynność.** Thonny ma menedżer pakietów (Manage packages), który pod spodem używa `pip`. W terminalu odpowiednikiem jest polecenie `pip install requests`. Komputery w pracowni mogą resetować zainstalowane pakiety między sesjami — dlatego na początku każdego labu trzeba sprawdzić, czy potrzebne biblioteki są dostępne, i w razie potrzeby zainstalować je ponownie.
:::

---

# Słowniki i listy

Słowniki (`dict`) i listy (`list`) to dwie struktury danych, z którymi będziesz pracować na każdych zajęciach. Dane pobierane z sieci (format JSON) to właśnie zagnieżdżone słowniki i listy.

## Słownik — przypomnienie

Słownik przechowuje pary klucz–wartość:

```python
student = {
    "imie": "Anna",
    "nazwisko": "Kowalska",
    "rok": 2
}

print(student["imie"])          # Anna
print(student["rok"])           # 2
```

Dodawanie i nadpisywanie:

```python
student["email"] = "anna@example.com"
student["rok"] = 3
print(student)
```

## Dostęp do zagnieżdżonych struktur

W praktyce dane rzadko są płaskie. Oto słownik zagnieżdżony — takie struktury będą się pojawiać w kursie regularnie:

```python
dataset = {
    "id": "830",
    "type": "dataset",
    "attributes": {
        "title": "Wykaz szkół i placówek oświatowych",
        "category": "Education",
        "modified": "2025-01-15"
    }
}

# Dostęp do tytułu — dwa poziomy w głąb:
print(dataset["attributes"]["title"])

# Dostęp do kategorii:
print(dataset["attributes"]["category"])
```

Czytaj od lewej do prawej: `dataset["attributes"]` zwraca wewnętrzny słownik, a `["title"]` wyciąga z niego wartość.

::: checkpoint
**Checkpoint:** Wypisz datę modyfikacji (`modified`) ze słownika `dataset`. Czy potrzebujesz jednego czy dwóch poziomów indeksowania?
:::

## Bezpieczny dostęp: `.get()`

Co się stanie, gdy klucz nie istnieje?

```python
print(dataset["attributes"]["description"])
# → KeyError: 'description'
```

Program się wysypie. Metoda `.get()` pozwala podać wartość domyślną:

```python
opis = dataset["attributes"].get("description", "(brak opisu)")
print(opis)  # (brak opisu)
```

Jeśli klucz istnieje — `.get()` zwróci jego wartość. Jeśli nie — zwróci to, co podasz jako drugi argument (tutaj: `"(brak opisu)"`). Bez drugiego argumentu zwróci `None`.

## Lista słowników

Odpowiedź API to zwykle **słownik**, który pod jednym z kluczy zawiera **listę** wyników. Każdy wynik to kolejny słownik. Zobaczmy samą listę — taką, jaką znajdziesz pod kluczem `"data"` w odpowiedzi:

```python
datasets = [
    {"id": "1", "attributes": {"title": "Jakość powietrza", "category": "Environment"}},
    {"id": "2", "attributes": {"title": "Szkoły w Warszawie", "category": "Education"}},
    {"id": "3", "attributes": {"title": "Rozkłady jazdy", "category": "Transport"}},
]
```

Dostęp do pojedynczego elementu:

```python
print(datasets[0]["attributes"]["title"])   # Jakość powietrza
print(datasets[2]["id"])                     # 3
```

Iteracja po wszystkich:

```python
for ds in datasets:
    title = ds["attributes"]["title"]
    cat = ds["attributes"].get("category", "?")
    print(f"  [{ds['id']}] {title} ({cat})")
```

## Ćwiczenie: zagnieżdżona struktura danych

Poniższy słownik imituje typową odpowiedź sieciowego źródła danych. Wklej go do nowego pliku w Thonnym:

```python
response = {
    "data": [
        {
            "id": "101",
            "type": "dataset",
            "attributes": {
                "title": "Dane meteorologiczne",
                "category": "Environment",
                "resources_count": 5
            }
        },
        {
            "id": "202",
            "type": "dataset",
            "attributes": {
                "title": "Budżety gmin",
                "category": "Finance",
                "resources_count": 12
            }
        },
        {
            "id": "303",
            "type": "dataset",
            "attributes": {
                "title": "Lista szkół podstawowych",
                "category": "Education"
            }
        },
    ],
    "meta": {
        "count": 1500
    }
}
```

Napisz kod, który:

1. Wypisuje łączną liczbę zbiorów z pola `meta → count`.
2. Wypisuje tytuły i kategorie wszystkich datasetów z listy `data`.
3. Wypisuje `resources_count` każdego datasetu. Uwaga: trzeci element nie ma tego pola — użyj `.get()`.

Spodziewany wynik:

```
Łączna liczba zbiorów: 1500

  [101] Dane meteorologiczne (Environment), zasoby: 5
  [202] Budżety gmin (Finance), zasoby: 12
  [303] Lista szkół podstawowych (Education), zasoby: ?
```

::: checkpoint
**Checkpoint:** Czy Twój kod wypisuje trzy linie z danymi i nie rzuca `KeyError` na trzecim elemencie? Jeśli tak — potrafisz nawigować po zagnieżdżonych słownikach i listach.
:::

---

# Funkcje

W dalszej części kursu będziemy zamykać powtarzalne operacje w funkcjach. Przygotujmy się do tego.

## Podstawowa funkcja

```python
def greet(name):
    """Zwraca powitanie."""
    return f"Cześć, {name}!"

msg = greet("Anna")
print(msg)  # Cześć, Anna!
```

Zwróć uwagę:

* `def` definiuje funkcję,
* `name` to **parametr** — zmienna lokalna, której wartość podajemy przy wywołaniu,
* `return` zwraca wynik — bez niego funkcja zwraca `None`,
* tekst w potrójnych cudzysłowach pod `def` to **docstring** — opis, co funkcja robi.

## Parametry domyślne

Parametr może mieć **wartość domyślną**. Wtedy podanie go przy wywołaniu jest opcjonalne:

```python
def greet(name, greeting="Cześć"):
    """Zwraca powitanie z konfigurowalną formą."""
    return f"{greeting}, {name}!"

print(greet("Anna"))              # Cześć, Anna!
print(greet("Anna", "Witaj"))     # Witaj, Anna!
```

Ten wzorzec pojawi się często — np. funkcja z domyślnym timeoutem lub limitem wyników:

```python
def fetch_data(url, timeout=10):
    ...
```

## Ćwiczenie: funkcja wyciągająca tytuły

Wróć do słownika `response` z poprzedniej sekcji. Napisz funkcję:

```python
def extract_titles(response_data):
    """Wyciąga tytuły datasetów z odpowiedzi API.
    
    Parameters
    ----------
    response_data : dict
        Słownik z kluczem "data" zawierającym listę datasetów.
    
    Returns
    -------
    list
        Lista tytułów (stringów).
    """
    # Twój kod tutaj
```

Przetestuj:

```python
titles = extract_titles(response)
print(titles)
# → ['Dane meteorologiczne', 'Budżety gmin', 'Lista szkół podstawowych']
```

::: key-concept
**Dlaczego warto zamykać kod w funkcjach?** Bo eliminujesz powtórzenia. Wzorzec jest prosty: weź powtarzający się blok → zamknij w `def` → parametryzuj to, co się zmienia.
:::

---

# Pętle i sterowanie przepływem

## `for` — iteracja po kolekcji

To już znasz z ćwiczeń ze słownikami. Uzupełnijmy o `enumerate`:

```python
owoce = ["jabłko", "banan", "cytryna"]

for i, owoc in enumerate(owoce, start=1):
    print(f"{i}. {owoc}")
```

Wynik:

```
1. jabłko
2. banan
3. cytryna
```

`enumerate` daje parę (indeks, element) — przydatne, gdy chcesz numerować wyniki.

## `while` z `break`

Częsty wzorzec w automatyzacji: pobieramy dane porcjami (strona po stronie), aż się skończą. Mechanizm: `while True` + warunek `break`.

Symulacja: mamy „strony" danych, pusta strona oznacza koniec:

```python
pages = [
    ["Anna", "Bartek", "Celina"],   # strona 1
    ["Dawid", "Ewa", "Filip"],       # strona 2
    ["Greta"],                        # strona 3
    [],                               # strona 4 — pusta, koniec
]

all_names = []
page_num = 0

while page_num < len(pages):
    page = pages[page_num]
    
    if not page:
        print("Pusta strona — koniec.")
        break
    
    all_names.extend(page)
    print(f"Strona {page_num + 1}: pobrano {len(page)} nazwisk "
          f"(łącznie: {len(all_names)})")
    
    page_num += 1

print(f"\nWszystkie nazwiska: {all_names}")
```

::: key-concept
**`extend` vs `append`.** `extend` dodaje *elementy* listy do listy (spłaszcza jeden poziom). `append` dodaje *całą listę* jako jeden element. Porównaj:

```python
a = [1, 2]
a.extend([3, 4])   # a == [1, 2, 3, 4]

b = [1, 2]
b.append([3, 4])   # b == [1, 2, [3, 4]]
```

Przy zbieraniu wyników ze stron prawie zawsze chcesz `extend`.
:::

## Ćwiczenie: zbieranie z limitem

Zmodyfikuj powyższy kod tak, żeby pobieranie zatrzymało się po zebraniu **co najmniej 4 nazwisk** (nawet jeśli są jeszcze kolejne strony). Wypisz zebrane nazwiska i numer ostatniej pobranej strony.

Wskazówka: `extend` dodaje całą stronę naraz, więc łączna liczba może przekroczyć limit — to normalne. Ważne, żeby pętla nie przechodziła do kolejnych stron.

::: checkpoint
**Checkpoint:** Czy Twój kod zatrzymuje się po stronie 2 (zebrano 6 nazwisk — przekroczono limit 4) i nie przetwarza strony 3? Strona 3 zawiera dane, więc to limit — a nie pusta strona — powoduje zatrzymanie.
:::

---

# Obsługa wyjątków

Gdy coś pójdzie nie tak — brakuje klucza, serwer nie odpowiada, plik nie istnieje — Python rzuca **wyjątek**. Bez obsługi wyjątków program się zatrzymuje. Z obsługą — może zareagować i kontynuować.

## Wyjątek bez obsługi

```python
numbers = [10, 20, 30]
print(numbers[5])
```

Wynik: `IndexError: list index out of range`. Program się kończy.

## `try` / `except`

```python
numbers = [10, 20, 30]

try:
    print(numbers[5])
except IndexError:
    print("Nie ma elementu o takim indeksie!")
```

Program wypisuje komunikat zamiast się wysypywać.

## Łapanie kilku typów wyjątków

W praktyce w jednym bloku `try` może wystąpić kilka różnych problemów:

```python
def get_value(data, key):
    """Pobiera wartość ze słownika i zamienia na int."""
    try:
        raw = data[key]
        return int(raw)
    except KeyError:
        print(f"Brak klucza: {key}")
        return None
    except ValueError:
        print(f"Wartość '{data[key]}' nie jest liczbą")
        return None

test = {"a": "42", "b": "xyz"}
print(get_value(test, "a"))    # 42
print(get_value(test, "b"))    # Wartość 'xyz' nie jest liczbą → None
print(get_value(test, "c"))    # Brak klucza: c → None
```

## Wzorzec z `raise`

Czasem chcesz złapać wyjątek, wypisać komunikat i **rzucić go dalej** (lub rzucić nowy):

```python
def safe_divide(a, b):
    """Dzieli a przez b z obsługą dzielenia przez zero."""
    try:
        return a / b
    except ZeroDivisionError:
        print(f"Nie można dzielić {a} przez 0")
        raise  # przekazuje wyjątek wyżej

# safe_divide(10, 0)  # wypisze komunikat I rzuci ZeroDivisionError
```

::: key-concept
**Wzorzec minimalny — zapamiętaj go, bo będzie wszędzie:**

```python
try:
    # operacja, która może się nie udać
    result = risky_operation()
except SpecificError as e:
    print(f"Błąd: {e}")
except Exception as e:
    print(f"Nieoczekiwany błąd: {e}")
```

W kursie `risky_operation()` to będzie np. zapytanie do serwera, parsowanie danych albo zapis pliku.
:::

## Ćwiczenie

Napisz funkcję `parse_ids(raw_list)`, która:

* przyjmuje listę stringów, np. `["1", "abc", "3", "", "5"]`,
* próbuje zamienić każdy element na `int`,
* elementy, które się nie konwertują — pomija (łapie `ValueError`),
* zwraca listę intów.

```python
result = parse_ids(["1", "abc", "3", "", "5"])
print(result)  # [1, 3, 5]
```

::: checkpoint
**Checkpoint:** Czy Twoja funkcja radzi sobie z pustymi stringami i tekstem, zwracając tylko poprawne liczby? Jeśli tak — umiesz obsługiwać błędy w pętli, co jest kluczowe przy automatycznym przetwarzaniu danych.
:::

---

# Pliki i katalogi

W kursie będziemy regularnie zapisywać pobrane dane do plików. Przygotujmy narzędzia.

## `pathlib` — praca ze ścieżkami

Moduł `pathlib` jest częścią biblioteki standardowej (nie trzeba instalować). Ścieżki są obiektami, nie stringami — dzięki temu kod jest czytelniejszy i działa na różnych systemach:

```python
from pathlib import Path

# Utwórz katalog (jeśli jeszcze nie istnieje)
output = Path("lab0_output")
output.mkdir(exist_ok=True)

print(f"Katalog: {output}")
print(f"Istnieje: {output.exists()}")
```

`exist_ok=True` oznacza: nie rzucaj błędu, jeśli katalog już istnieje.

## Zapis i odczyt tekstu

```python
file_path = output / "hello.txt"

# Zapis
file_path.write_text("Pierwsza linia\nDruga linia\n", encoding="utf-8")
print(f"Zapisano: {file_path}")

# Odczyt
content = file_path.read_text(encoding="utf-8")
print(content)
```

Operator `/` łączy fragmenty ścieżki — to odpowiednik `os.path.join()`, ale czytelniejszy.

## Zapis danych jako JSON

Format JSON jest standardem wymiany danych. Moduł `json` (biblioteka standardowa) pozwala konwertować struktury Pythona (słowniki, listy) na tekst JSON i odwrotnie:

```python
import json

data = [
    {"id": "1", "title": "Jakość powietrza"},
    {"id": "2", "title": "Szkoły w Warszawie"},
    {"id": "3", "title": "Rozkłady jazdy"},
]

json_path = output / "datasets.json"

# Zapis
json_text = json.dumps(data, ensure_ascii=False, indent=2)
json_path.write_text(json_text, encoding="utf-8")
print(f"Zapisano: {json_path}")
```

Parametr `ensure_ascii=False` zachowuje polskie znaki (zamiast `\u0142` zobaczysz `ł`). Parametr `indent=2` formatuje JSON z wcięciami — czytelny dla człowieka.

## Odczyt JSON z pliku

```python
loaded = json.loads(json_path.read_text(encoding="utf-8"))

print(type(loaded))       # <class 'list'>
print(len(loaded))        # 3
print(loaded[0]["title"])  # Jakość powietrza
```

`json.dumps()` zamienia obiekt Pythona → tekst JSON.
`json.loads()` zamienia tekst JSON → obiekt Pythona.

::: checkpoint
**Checkpoint:** Sprawdź, czy plik się zapisał. Wczytaj go z powrotem do Pythona i wypisz zawartość:

```python
check = json.loads(json_path.read_text(encoding="utf-8"))
print(check)
```

Czy widzisz listę trzech słowników z polskimi znakami (ł, ś, ó)?
:::

---

# f-stringi

f-stringi to sposób na wstawianie wartości zmiennych do tekstu. Będziemy ich używać wszędzie — w `print`, w konstruowaniu URL-i, w komunikatach.

## Podstawy

```python
name = "Anna"
age = 23
print(f"Studentka {name}, wiek: {age}")
```

Wewnątrz `{}` może być dowolne wyrażenie Pythona:

```python
items = [1, 2, 3, 4, 5]
print(f"Elementów: {len(items)}, suma: {sum(items)}")
```

## f-stringi ze słownikami

Przy pracy z danymi będziesz często wypisywać pola słownika:

```python
ds = {"id": "830", "attributes": {"title": "Wykaz szkół"}}

print(f"  [{ds['id']}] {ds['attributes']['title']}")
```

Zwróć uwagę na cudzysłowy: f-string jest w podwójnych (`"`), więc klucze słownika muszą być w pojedynczych (`'`). Można też odwrotnie.

## Formatowanie liczb

```python
size = 1234567
print(f"Rozmiar: {size:,} bajtów")     # 1,234,567 bajtów

ratio = 0.8567
print(f"Postęp: {ratio:.1%}")          # 85.7%
```

---

# Ćwiczenie podsumowujące

To ćwiczenie łączy wszystkie elementy z tego labu.

## Zadanie

Dana jest lista `records` symulująca dane pobrane z sieci:

```python
records = {
    "data": [
        {"id": "10", "attributes": {"title": "Pomiary hałasu", "format": "CSV"}},
        {"id": "20", "attributes": {"title": "Emisje CO2"}},
        {"id": "30", "attributes": {"title": "Stacje pogodowe", "format": "JSON"}},
        {"id": "40", "attributes": {"title": "Zużycie wody", "format": "XML"}},
        {"id": "50", "attributes": {"title": "Jakość gleby", "format": "CSV"}},
    ],
    "meta": {"count": 200}
}
```

Napisz funkcję `save_summary(response, output_dir, max_items=None)`:

1. Parametr `response` to słownik jak wyżej.
2. Parametr `output_dir` to ścieżka katalogu wyjściowego (string lub `Path`).
3. Parametr `max_items` (domyślnie `None` = bez limitu) ogranicza liczbę przetwarzanych elementów.
4. Funkcja iteruje po elementach z `response["data"]` (najwyżej `max_items`, jeśli podany).
5. Dla każdego elementu tworzy słownik `{"id": ..., "title": ..., "format": ...}`, wyciągając dane z `attributes`. Brak klucza `format` → wartość domyślna `"unknown"`.
6. Zbiera słowniki w listę i zapisuje do pliku `summary.json` w `output_dir`.
7. Obsługuje ewentualny `KeyError` (gdyby `attributes` nie było) — pomija taki element i wypisuje ostrzeżenie.
8. Zwraca liczbę zapisanych elementów.

Przetestuj:

```python
from pathlib import Path

output = Path("lab0_output")
output.mkdir(exist_ok=True)

n = save_summary(records, output)
print(f"Zapisano {n} elementów")

n = save_summary(records, output, max_items=3)
print(f"Zapisano {n} elementów (z limitem)")
```

Spodziewany wynik:

```
Zapisano 5 elementów
Zapisano 3 elementów (z limitem)
```

Sprawdź plik `lab0_output/summary.json` — powinien zawierać listę słowników z polami `id`, `title`, `format`.

::: checkpoint
**Checkpoint:** Czy Twoja funkcja poprawnie obsługuje brak klucza `format` (→ `"unknown"`), limit `max_items` i zapis do JSON? Jeśli tak — masz solidne podstawy Pythona do dalszej pracy w kursie.
:::

---

# Zadania dodatkowe

Poniższe zadania są **opcjonalne** — dla osób, które skończyły wcześniej. Poruszają tematy, które przydadzą się w dalszej części kursu.

## Zadanie A: list comprehension

Przepisz funkcję `extract_titles` z sekcji „Funkcje" tak, żeby używała list comprehension zamiast pętli:

```python
def extract_titles(response_data):
    return [...]  # jedna linia
```

Rozszerzenie: napisz wersję, która zwraca tylko tytuły datasetów z kategorii `"Environment"`.

## Zadanie B: słownik z listy

Mając listę `records["data"]`, utwórz słownik mapujący `id → title`:

```python
# Spodziewany wynik:
# {"10": "Pomiary hałasu", "20": "Emisje CO2", ...}
```

Użyj dict comprehension.

## Zadanie C: obsługa wielu plików

Napisz funkcję `save_per_format(response, output_dir)`, która:

1. Grupuje datasety według formatu (`CSV`, `JSON`, `XML`, `unknown`).
2. Dla każdego formatu zapisuje osobny plik, np. `CSV.json`, `JSON.json`, `unknown.json`.
3. Zwraca słownik `{format: count}`.

Wskazówka: użyj `dict` z listami jako wartościami albo `collections.defaultdict(list)`.

---

# Podsumowanie

W tym labie:

* skonfigurowałeś środowisko (Thonny, Python, instalacja pakietów),
* przećwiczyłeś nawigację po zagnieżdżonych słownikach i listach — klucz do pracy z danymi w formacie JSON,
* napisałeś funkcje z parametrami domyślnymi i docstringami,
* opanowałeś pętle `for` i `while` z `break` i `extend`,
* obsłużyłeś wyjątki (`try` / `except`) — bez tego żaden skrypt automatyzujący nie przetrwa kontaktu z rzeczywistością,
* zapisałeś dane do pliku JSON z użyciem `pathlib`.

Na następnych zajęciach wykorzystamy te umiejętności w praktyce — zaczniemy pobierać dane z sieci.