# Znajdź wszystkie pliki .md
SRCS = $(shell find . -name '*.md')
# Zamień .md na .html w liście plików
OBJS = $(SRCS:.md=.html)

# Domyślna reguła
all: $(OBJS)

# Reguła budowania: używamy skryptu panwater.sh zamiast wpisywać pandoc ręcznie
%.html: %.md _config/style.html ./panwater.sh
	@./panwater.sh $<

clean:
	rm -f $(OBJS)