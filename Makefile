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
PTY_TEST_BINARY ?= ./cshell
PTY_TEST_SUITE ?= tests/fixtures/prototype-pty.json
PTY_TEST_TARGET ?= cshell
PTY_TEST_CASE ?=

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
LEXER_HEADERS = include/cshell/lexer.h include/cshell/input.h
ALIAS_HEADERS = include/cshell/alias.h include/cshell/input.h
PARSER_HEADERS = $(ALIAS_HEADERS) include/cshell/parser.h include/cshell/ast.h include/cshell/quote.h $(LEXER_HEADERS)
PARSER_OBJECTS = build/alias.o build/parser.o build/ast.o build/lexer.o build/input.o build/quote.o
PARSER_FAULT_OBJECTS = build/tests/parser-fault-alias.o build/tests/parser-fault-parser.o build/tests/parser-fault-ast.o \
	build/tests/parser-fault-lexer.o build/tests/parser-fault-input.o build/tests/parser-fault-quote.o
STATE_HEADERS = include/cshell/state.h $(INPUT_HEADERS)
EXPAND_HEADERS = include/cshell/expand.h include/cshell/arithmetic.h include/cshell/quote.h $(LEXER_HEADERS) $(STATE_HEADERS)
EXPAND_OBJECTS = build/expand.o build/quote.o build/arithmetic.o
EXECUTE_HEADERS = include/cshell/execute.h include/cshell/redirect.h $(PARSER_HEADERS) $(STATE_HEADERS)
EXECUTE_OBJECTS = build/execute.o build/redirect.o $(PARSER_OBJECTS) build/state.o
EXECUTE_FAULT_OBJECTS = build/tests/execute-fault-execute.o build/tests/execute-fault-redirect.o
FIELDS_HEADERS = $(EXPAND_HEADERS) src/field_internal.h
FIELDS_OBJECTS = build/fields.o build/pathname.o
FIELDS_FAULT_OBJECTS = build/tests/fields-fault-fields.o build/tests/fields-fault-pathname.o

.PHONY: all test test-input test-lexer test-parser test-alias test-state test-expand test-fields test-execute test-pipeline test-pty test-harness docker-build docker-test docker-test-pty docker-shell clean

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

build/lexer.o: src/lexer.c $(LEXER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/lexer_fixture: tests/lexer_fixture.c build/lexer.o $(LEXER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/lexer_fixture.c build/lexer.o $(LDLIBS)

build/tests/fault-lexer.o: src/lexer.c $(LEXER_HEADERS) tests/lexer_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/lexer_faults.h -c $< -o $@

build/tests/lexer_faults: tests/lexer_faults.c tests/lexer_faults.h build/tests/fault-lexer.o $(LEXER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/lexer_faults.c build/tests/fault-lexer.o $(LDLIBS)

test-lexer: build/tests/lexer_fixture build/tests/lexer_faults
	$(PYTHON) tests/lexer.py build/tests/lexer_fixture --fault-binary build/tests/lexer_faults

build/parser.o build/ast.o: build/%.o: src/%.c $(PARSER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/quote.o: src/quote.c include/cshell/quote.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/parser_fixture: tests/parser_fixture.c $(PARSER_OBJECTS) $(PARSER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/parser_fixture.c $(PARSER_OBJECTS) $(LDLIBS)

build/tests/ast_fixture: tests/ast_fixture.c build/ast.o build/lexer.o $(PARSER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/ast_fixture.c build/ast.o build/lexer.o $(LDLIBS)

$(PARSER_FAULT_OBJECTS): build/tests/parser-fault-%.o: src/%.c $(PARSER_HEADERS) tests/parser_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/parser_faults.h -c $< -o $@

build/tests/parser_faults: tests/parser_faults.c tests/parser_faults.h $(PARSER_FAULT_OBJECTS) $(PARSER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/parser_faults.c $(PARSER_FAULT_OBJECTS) $(LDLIBS)

test-parser: build/tests/parser_fixture build/tests/parser_faults build/tests/ast_fixture
	$(PYTHON) tests/parser.py build/tests/parser_fixture --fault-binary build/tests/parser_faults
	./build/tests/ast_fixture

build/alias.o: src/alias.c $(ALIAS_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/alias_storage: tests/alias_storage.c build/alias.o $(ALIAS_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/alias_storage.c build/alias.o $(LDLIBS)

build/tests/alias_lexer: tests/alias_lexer.c build/lexer.o $(LEXER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/alias_lexer.c build/lexer.o $(LDLIBS)

build/tests/alias_parser: tests/alias_parser.c $(PARSER_OBJECTS) $(PARSER_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/alias_parser.c $(PARSER_OBJECTS) $(LDLIBS)

build/tests/fault-alias.o: src/alias.c $(ALIAS_HEADERS) tests/alias_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/alias_faults.h -c $< -o $@

build/tests/alias_faults: tests/alias_faults.c tests/alias_faults.h build/tests/fault-alias.o $(ALIAS_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/alias_faults.c build/tests/fault-alias.o $(LDLIBS)

test-alias: build/tests/alias_storage build/tests/alias_lexer build/tests/alias_parser build/tests/alias_faults
	$(PYTHON) tests/smoke.py ./build/tests/alias_storage --suite tests/fixtures/alias.json
	$(PYTHON) tests/smoke.py ./build/tests/alias_lexer --suite tests/fixtures/alias.json
	$(PYTHON) tests/smoke.py ./build/tests/alias_parser --suite tests/fixtures/alias.json
	$(PYTHON) tests/smoke.py ./build/tests/alias_faults --suite tests/fixtures/alias.json

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

build/expand.o build/arithmetic.o: build/%.o: src/%.c $(EXPAND_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/expand_fixture: tests/expand_fixture.c $(EXPAND_OBJECTS) build/state.o build/lexer.o $(EXPAND_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/expand_fixture.c $(EXPAND_OBJECTS) build/state.o build/lexer.o $(LDLIBS)

build/tests/fault-expand.o build/tests/fault-quote.o: build/tests/fault-%.o: src/%.c $(EXPAND_HEADERS) tests/expand_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/expand_faults.h -c $< -o $@

build/tests/expand_faults: tests/expand_faults.c tests/expand_faults.h build/tests/fault-expand.o build/tests/fault-quote.o build/arithmetic.o build/state.o build/lexer.o $(EXPAND_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/expand_faults.c build/tests/fault-expand.o build/tests/fault-quote.o build/arithmetic.o build/state.o build/lexer.o $(LDLIBS)

build/tests/arithmetic_fixture: tests/arithmetic_fixture.c build/arithmetic.o build/state.o $(EXPAND_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/arithmetic_fixture.c build/arithmetic.o build/state.o $(LDLIBS)

build/tests/quote_fixture: tests/quote_fixture.c build/quote.o include/cshell/quote.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/quote_fixture.c build/quote.o $(LDLIBS)

build/tests/arith-fault-arithmetic.o build/tests/arith-fault-state.o: build/tests/arith-fault-%.o: src/%.c $(EXPAND_HEADERS) tests/arithmetic_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/arithmetic_faults.h -c $< -o $@

build/tests/arithmetic_faults: tests/arithmetic_faults.c tests/arithmetic_faults.h build/tests/arith-fault-arithmetic.o build/tests/arith-fault-state.o $(EXPAND_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/arithmetic_faults.c build/tests/arith-fault-arithmetic.o build/tests/arith-fault-state.o $(LDLIBS)

$(FIELDS_OBJECTS): build/%.o: src/%.c $(FIELDS_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/fields_fixture: tests/fields_fixture.c $(FIELDS_OBJECTS) $(EXPAND_OBJECTS) build/state.o build/lexer.o $(FIELDS_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/fields_fixture.c $(FIELDS_OBJECTS) $(EXPAND_OBJECTS) build/state.o build/lexer.o $(LDLIBS)

$(FIELDS_FAULT_OBJECTS): build/tests/fields-fault-%.o: src/%.c $(FIELDS_HEADERS) tests/fields_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/fields_faults.h -c $< -o $@

build/tests/fields_faults: tests/fields_faults.c tests/fields_faults.h $(FIELDS_FAULT_OBJECTS) build/state.o $(FIELDS_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/fields_faults.c $(FIELDS_FAULT_OBJECTS) build/state.o $(LDLIBS)

test-fields: build/tests/fields_fixture build/tests/fields_faults
	$(PYTHON) tests/fields.py build/tests/fields_fixture --fault-binary build/tests/fields_faults

test-expand: test-fields build/tests/arithmetic_faults build/tests/expand_fixture build/tests/expand_faults build/tests/arithmetic_fixture build/tests/quote_fixture
	$(PYTHON) tests/smoke.py ./build/tests/expand_fixture --suite tests/fixtures/expand.json
	$(PYTHON) tests/smoke.py ./build/tests/expand_faults --suite tests/fixtures/expand-faults.json
	$(PYTHON) tests/smoke.py ./build/tests/arithmetic_fixture --suite tests/fixtures/arithmetic.json
	$(PYTHON) tests/smoke.py ./build/tests/quote_fixture --suite tests/fixtures/quote.json
	$(PYTHON) tests/smoke.py ./build/tests/arithmetic_faults --suite tests/fixtures/arithmetic-faults.json

build/execute.o build/redirect.o: build/%.o: src/%.c $(EXECUTE_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -c $< -o $@

build/tests/execute_fixture: tests/execute_fixture.c $(EXECUTE_OBJECTS) $(EXECUTE_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/execute_fixture.c $(EXECUTE_OBJECTS) $(LDLIBS)

build/tests/execute_helper: tests/execute_helper.c
	mkdir -p $(dir $@)
	# The helper observes descriptors after exec; sanitizer startup can reopen
	# intentionally closed standard descriptors before main on macOS.
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(filter-out -fsanitize=%,$(CFLAGS)) \
		$(filter-out -fsanitize=%,$(LDFLAGS)) -o $@ $< $(LDLIBS)

$(EXECUTE_FAULT_OBJECTS): build/tests/execute-fault-%.o: src/%.c $(EXECUTE_HEADERS) tests/execute_faults.h
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) -include tests/execute_faults.h -c $< -o $@

build/tests/execute_faults: tests/execute_faults.c tests/execute_faults.h $(EXECUTE_FAULT_OBJECTS) $(PARSER_OBJECTS) build/state.o $(EXECUTE_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/execute_faults.c $(EXECUTE_FAULT_OBJECTS) $(PARSER_OBJECTS) build/state.o $(LDLIBS)

test-execute: build/tests/execute_fixture build/tests/execute_helper build/tests/execute_faults
	$(PYTHON) tests/execute.py build/tests/execute_fixture --helper build/tests/execute_helper --fault-binary build/tests/execute_faults

build/tests/pipeline_fixture: tests/pipeline_fixture.c $(EXECUTE_OBJECTS) $(EXECUTE_HEADERS)
	mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ tests/pipeline_fixture.c $(EXECUTE_OBJECTS) $(LDLIBS)

test-pipeline: build/tests/execute_fixture build/tests/execute_helper build/tests/pipeline_fixture build/tests/execute_faults
	$(PYTHON) tests/pipeline.py build/tests/execute_fixture --helper build/tests/execute_helper --api-binary build/tests/pipeline_fixture --fault-binary build/tests/execute_faults

test: $(TEST_TARGET) test-input test-lexer test-parser test-alias test-state test-expand test-execute test-pipeline
	$(PYTHON) tests/smoke.py "$(TEST_BINARY)" --suite "$(TEST_SUITE)" \
		--timeout "$(TEST_TIMEOUT)" --output-limit "$(TEST_OUTPUT_LIMIT)" $(if $(strip $(TEST_CASE)),--case "$(TEST_CASE)")

test-pty: $(PTY_TEST_TARGET)
	$(PYTHON) tests/smoke.py "$(PTY_TEST_BINARY)" --suite "$(PTY_TEST_SUITE)" \
		--timeout "$(TEST_TIMEOUT)" --output-limit "$(TEST_OUTPUT_LIMIT)" $(if $(strip $(PTY_TEST_CASE)),--case "$(PTY_TEST_CASE)")

test-harness:
	$(PYTHON) -m unittest discover -s tests -p 'test_*harness.py' -v

docker-build:
	$(DOCKER) build --tag "$(DOCKER_IMAGE)" --build-arg "TEST_TARGET=$(TEST_TARGET)" .

docker-test: docker-build
	$(DOCKER) run --rm --init "$(DOCKER_IMAGE)" make test \
		"TEST_BINARY=$(TEST_BINARY)" "TEST_SUITE=$(TEST_SUITE)" \
		"TEST_TARGET=$(TEST_TARGET)" "TEST_TIMEOUT=$(TEST_TIMEOUT)" \
		"TEST_OUTPUT_LIMIT=$(TEST_OUTPUT_LIMIT)" "TEST_CASE=$(TEST_CASE)"

docker-test-pty:
	$(MAKE) docker-build "TEST_TARGET=$(PTY_TEST_TARGET)"
	$(DOCKER) run --rm --init "$(DOCKER_IMAGE)" make test-pty \
		"PTY_TEST_BINARY=$(PTY_TEST_BINARY)" "PTY_TEST_SUITE=$(PTY_TEST_SUITE)" \
		"PTY_TEST_TARGET=$(PTY_TEST_TARGET)" "TEST_TIMEOUT=$(TEST_TIMEOUT)" \
		"TEST_OUTPUT_LIMIT=$(TEST_OUTPUT_LIMIT)" "PTY_TEST_CASE=$(PTY_TEST_CASE)"

docker-shell: docker-build
	$(DOCKER) run --rm --init -it "$(DOCKER_IMAGE)" /bin/sh

clean:
	rm -rf build cshell
