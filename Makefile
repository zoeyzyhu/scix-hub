PYTHON ?= python

.PHONY: up sync sync-check install-repos doctor cheat test ci

up:
	$(PYTHON) -m scix up

sync:
	$(PYTHON) -m scix sync

sync-check:
	$(PYTHON) -m scix sync --check

install-repos:
	$(PYTHON) -m scix install-repos

doctor:
	$(PYTHON) -m scix doctor

cheat:
	$(PYTHON) -m scix cheat

test:
	$(PYTHON) -m pytest -q

ci:
	pre-commit run --files
	$(PYTHON) -m pytest -q
	$(PYTHON) -m scix sync
