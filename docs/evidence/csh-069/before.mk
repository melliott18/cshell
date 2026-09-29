# Additional makefile for the retained pre-repair fixture plus diagnostic hook.
CSH069_EVIDENCE_DIR ?= docs/evidence/csh-069
build/tests/context_before: $(CSH069_EVIDENCE_DIR)/before_fixture.c build/tests/context-schedule-execute.o $(EXECUTE_OBJECTS) build/character.o
	$(CC) $(CPPFLAGS) $(CSHELL_CPPFLAGS) $(CFLAGS) $(LDFLAGS) -DCSH_CONTEXT_SCHEDULE -o $@ $< build/tests/context-schedule-execute.o $(filter-out build/execute.o,$(EXECUTE_OBJECTS)) build/character.o $(LDLIBS)
