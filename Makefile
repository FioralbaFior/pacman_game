PYTHON  ?= python3
CONFIG  ?= config.json
WHEEL   := $(firstword $(wildcard mazegenerator-*.whl))
MYPY_FLAGS := --warn-return-any --warn-unused-ignores \
              --ignore-missing-imports --disallow-untyped-defs \
              --check-untyped-defs

.PHONY: install run debug clean lint lint-strict test package

install:
	$(PYTHON) -m pip install -r requirements.txt
	@test -n "$(WHEEL)" || \
	  (echo "Missing assigned mazegenerator wheel at the repo root" && exit 1)
	$(PYTHON) -m pip install --force-reinstall "$(WHEEL)"

run:
	$(PYTHON) pac-man.py $(CONFIG)

debug:
	$(PYTHON) -m pdb pac-man.py $(CONFIG)

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache build dist
	find . -type f -name '*.py[co]' -delete

lint:
	flake8 .
	mypy . $(MYPY_FLAGS)

lint-strict:
	flake8 .
	mypy . --strict --ignore-missing-imports

test:
	$(PYTHON) -m unittest discover -s tests -v

package:
	$(PYTHON) -m PyInstaller pacman.spec --clean --noconfirm
