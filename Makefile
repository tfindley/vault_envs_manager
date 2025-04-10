# Makefile for vaultenvmanager

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
SCRIPT := main.py
OUTPUT_FILE := test.env

.PHONY: help run test format clean venv install

help:
	@echo "VaultEnvManager Makefile Commands:"
	@echo ""
	@echo "  make venv        Set up a Python virtual environment"
	@echo "  make install     Install required Python packages"
	@echo "  make run         Run script interactively"
	@echo "  make test        Run and write output to $(OUTPUT_FILE)"
	@echo "  make format      Auto-format Python code using black"
	@echo "  make clean       Remove virtualenv and test output"
	@echo ""

venv:
	@echo "Creating virtual environment..."
	@test -d $(VENV) || python3 -m venv $(VENV)

install: venv
	@echo "Installing Python dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: $(SCRIPT)
	@echo "Running vaultenvmanager..."
	$(PYTHON) $(SCRIPT)

test: $(SCRIPT)
	@echo "Writing env output to $(OUTPUT_FILE)..."
	$(PYTHON) $(SCRIPT) \
		token \
		--vault-addr=http://127.0.0.1:8200 \
		--kv-engine=kv_user_tristan \
		--kv-path=testenv \
		--output=env \
		--output-file=$(OUTPUT_FILE) \
		--env-token-var=VAULT_TOKEN \
		-t $$VAULT_TOKEN \
		--ca-cert=~/ssl/vibsubca.vault.pem

format:
	@echo "Formatting with black..."
	black .

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV) $(OUTPUT_FILE) __pycache__ .pytest_cache
