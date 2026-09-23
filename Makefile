CC ?= cc
CFLAGS ?= -Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2
CPPFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
PYTHON ?= python3
DOCKER ?= docker
DOCKER_IMAGE ?= cshell-test:local
TEST_BINARY ?= ./cshell
TEST_SUITE ?= tests/fixtures/prototype.json
# Clear TEST_TARGET when testing an already available executable, e.g. /bin/sh.
TEST_TARGET ?= cshell
TEST_TIMEOUT ?= 5
TEST_OUTPUT_LIMIT ?= 65536
TEST_CASE ?=

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
STATE_HEADERS = include/cshell/state.h $(INPUT_HEADERS)

.PHONY: all test test-input test-state test-harness docker-build docker-test docker-shell clean

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

build/state.o: src/state.c $(STATE_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/state_fixture: tests/state_fixture.c build/state.o $(INPUT_OBJECTS) $(STATE_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/state_fixture.c build/state.o $(INPUT_OBJECTS) $(LDLIBS)

build/tests/fault-state.o: src/state.c $(STATE_HEADERS) tests/state_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/state_faults.h -c $< -o $@

build/tests/state_faults: tests/state_faults.c tests/state_faults.h build/tests/fault-state.o $(STATE_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/state_faults.c build/tests/fault-state.o $(LDLIBS)

test-state: build/tests/state_fixture build/tests/state_faults
	$(PYTHON) tests/smoke.py ./build/tests/state_fixture --suite tests/fixtures/state.json
	$(PYTHON) tests/smoke.py ./build/tests/state_faults --suite tests/fixtures/state-faults.json

test: $(TEST_TARGET) test-input test-state
	$(PYTHON) tests/smoke.py "$(TEST_BINARY)" --suite "$(TEST_SUITE)" \
		--timeout "$(TEST_TIMEOUT)" --output-limit "$(TEST_OUTPUT_LIMIT)" $(if $(strip $(TEST_CASE)),--case "$(TEST_CASE)")

test-harness:
	$(PYTHON) -m unittest discover -s tests -p 'test_harness.py' -v

docker-build:
	$(DOCKER) build --tag "$(DOCKER_IMAGE)" --build-arg "TEST_TARGET=$(TEST_TARGET)" .

docker-test: docker-build
	$(DOCKER) run --rm --init "$(DOCKER_IMAGE)" make test \
		"TEST_BINARY=$(TEST_BINARY)" "TEST_SUITE=$(TEST_SUITE)" \
		"TEST_TARGET=$(TEST_TARGET)" "TEST_TIMEOUT=$(TEST_TIMEOUT)" \
		"TEST_OUTPUT_LIMIT=$(TEST_OUTPUT_LIMIT)" "TEST_CASE=$(TEST_CASE)"

docker-shell: docker-build
	$(DOCKER) run --rm --init -it "$(DOCKER_IMAGE)" /bin/sh

clean:
	rm -rf build cshell
