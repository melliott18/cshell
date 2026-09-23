CC ?= cc
CFLAGS ?= -Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2
CPPFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
PYTHON ?= python3
DOCKER ?= docker
DOCKER_IMAGE ?= cshell-test:local

# GNU make defines LEX=lex by default; use flex unless explicitly overridden.
ifeq ($(origin LEX),default)
LEX = flex
endif
LEX ?= flex
LEXFLAGS ?=

CSHELL_CPPFLAGS = -D_POSIX_C_SOURCE=200809L -Iinclude
OBJECTS = build/main.o build/legacy/execute.o build/legacy/lexer.o

.PHONY: all test docker-build docker-test docker-shell clean

all: cshell

cshell: $(OBJECTS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(OBJECTS) $(LDLIBS)

build/%.o: src/%.c include/cshell/legacy.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/legacy/lexer.c: src/legacy/lexer.l
	mkdir -p $(dir $@)
	$(LEX) $(LEXFLAGS) -o $@ $<

build/legacy/lexer.o: build/legacy/lexer.c include/cshell/legacy.h
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

test: cshell
	$(PYTHON) tests/smoke.py ./cshell

docker-build:
	$(DOCKER) build --tag "$(DOCKER_IMAGE)" .

docker-test: docker-build
	$(DOCKER) run --rm --init "$(DOCKER_IMAGE)"

docker-shell: docker-build
	$(DOCKER) run --rm --init -it "$(DOCKER_IMAGE)" /bin/sh

clean:
	rm -rf build cshell
