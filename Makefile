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
INPUT_OBJECTS = build/input.o build/invocation.o
INPUT_HEADERS = include/cshell/input.h include/cshell/invocation.h
INPUT_FAULT_OBJECTS = build/tests/fault-input.o build/tests/fault-invocation.o

.PHONY: all test test-input docker-build docker-test docker-shell clean

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

$(INPUT_OBJECTS): build/%.o: src/%.c $(INPUT_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/input_fixture: tests/input_fixture.c $(INPUT_OBJECTS) $(INPUT_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/input_fixture.c $(INPUT_OBJECTS) $(LDLIBS)

$(INPUT_FAULT_OBJECTS): build/tests/fault-%.o: src/%.c $(INPUT_HEADERS) tests/input_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/input_faults.h -c $< -o $@

build/tests/input_faults: tests/input_faults.c tests/input_faults.h $(INPUT_FAULT_OBJECTS) $(INPUT_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/input_faults.c $(INPUT_FAULT_OBJECTS) $(LDLIBS)

test-input: build/tests/input_fixture build/tests/input_faults
	$(PYTHON) tests/input.py build/tests/input_fixture --fault-binary build/tests/input_faults

test: cshell test-input
	$(PYTHON) tests/smoke.py ./cshell

docker-build:
	$(DOCKER) build --tag "$(DOCKER_IMAGE)" .

docker-test: docker-build
	$(DOCKER) run --rm --init "$(DOCKER_IMAGE)"

docker-shell: docker-build
	$(DOCKER) run --rm --init -it "$(DOCKER_IMAGE)" /bin/sh

clean:
	rm -rf build cshell
