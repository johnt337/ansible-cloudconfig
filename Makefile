MAKEFLAGS  += --no-builtin-rules
.SUFFIXES:
.SECONDARY:
.DELETE_ON_ERROR:

SRC   ?= $(shell find . -name '*.py')
ARGS  ?= -v -race
PROJ  ?= ansible-cloudconfig
DEP   ?= github.com/johnt337/cloudconfig
MOUNT ?= $(shell pwd)
DEP_MOUNT ?= "$(shell pwd)/../cloudconfig"
ANSIBLE ?= /Users/johnt/gitroot/ansible

clean:
	@echo "running make clean"

distclean:
	@make clean
	@echo "running make distclean"

interactive:
	@echo "running make interactive"
	docker run -it --rm --name cloudconfig-build -v /var/run:/var/run -v $(MOUNT):/workspace/$(PROJ) -v $(DEP_MOUNT):/go/src/$(DEP) -v $(ANSIBLE):/ansible --entrypoint=/bin/bash -i cloudconfig 

lint: $(SRC)
	@echo "running lint"

lint-check: $(SRC)
	@echo "running lint-check"

test: $(SRC)
	@echo "running test"

test-cover: $(SRC)
	@echo "running test-cover"

.PHONY: clean distclean interactive lint lint-check test test-cover
