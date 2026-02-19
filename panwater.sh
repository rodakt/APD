#!/bin/bash

# 1. Ustalanie ścieżki do skryptu i konfiguracji
# To magiczna linijka, która znajduje katalog, w którym leży TEN skrypt.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STYLE_FILE="$REPO_ROOT/_config/style.html"

# 2. Walidacja wejścia
if [ -z "$1" ]; then
    echo "Użycie: ./panwater ścieżka/do/pliku.md [typ]"
    exit 1
fi

INPUT_FILE="$1"
# Wyciągnięcie nazwy pliku bez ścieżki i rozszerzenia
FILENAME=$(basename -- "$INPUT_FILE")
EXTENSION="${FILENAME##*.}"
FILENAME_NO_EXT="${FILENAME%.*}"
# Ustalenie katalogu wyjściowego (tam gdzie plik wejściowy)
OUTPUT_DIR=$(dirname "$INPUT_FILE")
OUTPUT_FILE="$OUTPUT_DIR/$FILENAME_NO_EXT.html"

# 3. Logika Lab vs Wykład
# Domyślnie Wykład
TOC_OPTS="--toc"
MSG_TYPE="WYKŁAD"

# Jeśli w nazwie pliku jest 'lab' LUB drugi argument to 'lab'
if [[ "${FILENAME,,}" == *"lab"* ]] || [[ "$2" == "lab" ]]; then
    # TOC_OPTS=""
    MSG_TYPE="LABORATORIUM"
fi

echo "Generowanie ($MSG_TYPE): $INPUT_FILE -> $OUTPUT_FILE"

# 4. Uruchomienie Pandoc
# Zauważ użycie "$STYLE_FILE" z pełną ścieżką
pandoc "$INPUT_FILE" \
    -s \
    $TOC_OPTS \
    --number-sections \
    --mathjax \
    -c https://cdn.jsdelivr.net/npm/water.css@2/out/water.css \
    -H "$STYLE_FILE" \
    --syntax-highlight pygments \
    -o "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo -e "✔ Gotowe!"
else
    echo -e "✘ Błąd!"
    exit 1
fi