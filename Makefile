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


build-ansible/cloudconfig:
	@echo "running make build-ansible/cloudconfig"
	docker build -t ansible/cloudconfig -f Dockerfile .

clean:
	@echo "running make clean"
	docker images | grep -E '<none>' | awk '{print$$3}' | xargs docker rmi

distclean:
	@make clean
	@echo "running make distclean"
	docker rmi ansible/cloudconfig

interactive:
	@echo "running make interactive"
	docker run -it --rm --name ansible-dev -v /var/run:/var/run -v $(MOUNT):/workspace/$(PROJ) -v $(DEP_MOUNT):/go/src/$(DEP) -v $(ANSIBLE):/ansible --entrypoint=/workspace/ansible-cloudconfig/init_ansible_env.sh -i ansible/cloudconfig

lint: $(SRC)
	@echo "running lint"

lint-check: $(SRC)
	@echo "running lint-check"

test: $(SRC)
	@echo "running test"
	ansible-test-module -m ./files/library/cloudconfig_user.py -a "state='present' name='afoobar' passwd='$fdsfdsfsfdfdfsfd$laX2u7GGpuo7RVS.4fZgQ8.Iav7gQVbDn4NkM98kxfdsfdsfsdfl0SStGX.LI6.hmXUjafOU3hoJtUScT0FOIMtmHMa.' ssh_authorized_keys='ssh-rsa dfsffsdjfhsdNCyIs6qO6sXs/DUZcfdfsdfsfdsdfFb9UwRedNgv67FQI3iaIXRALuqRNBqGgnST9/i1GFmd8yKkjMwojsCyqn5sjCrnRoNrgwgwlrSRSuOn4ema7pEVkFhMgrE5Kf2b8gC/MEu+rPOgERH1SihejToyqcCpJdMcxTiSwSkI57maxlc3Upt00rw5GYP2J9yjWzkLokA4ED4iyoaXrplzcnTmfiTllveOD6XivTgXdl4n9kUxak7jZZgQ8RVlVLbvJbTDSe8LNvee0CmFnduI9FwsaBpIVgEz3V john.torres@routetodigital.com'"

test-cover: $(SRC)
	@echo "running test-cover"

.PHONY: clean distclean interactive lint lint-check test test-cover
