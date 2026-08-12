.DEFAULT_GOAL := help
COMPOSE ?= docker compose
SERVICE ?= main
SHELL := /bin/bash
TAGS_FILE := .tags

ifeq ($(CI),true)
	COMPOSE_RUN_FLAGS := --rm -T
else
	COMPOSE_RUN_FLAGS := --rm -it
endif
COMPOSE_RUN := $(COMPOSE) run $(COMPOSE_RUN_FLAGS)
ENV_TYPE ?= production

ifeq ($(shell echo "$(ENV_TYPE)" | tr A-Z a-z),development)
	COMMAND_RUN :=
else
	COMMAND_RUN := $(COMPOSE_RUN) $(SERVICE)
endif

.PHONY: bash bash-root build build-no-cache clean container-clean help kill lint lint-check logs restart run start stop tags test tse

bash:					# Open a Bash shell in the application container
	$(COMMAND_RUN) bash

bash-root:				# Open a Bash shell as root in a new application container
	$(COMPOSE_RUN) --user root $(SERVICE) bash

build:					# Pull base images and build the application image
	$(COMPOSE) pull
	$(COMPOSE) build

build-no-cache:			# Build the application image without cache
	$(COMPOSE) pull
	$(COMPOSE) build --no-cache

clean:					# Remove local temporary files and coverage data
	rm -f $(TAGS_FILE)
	find . -type f \( -name '*.pyc' -o -name '*~' \) -delete
	rm -rf $(TAGS_FILE) *.egg-info .coverage .mypy_cache .pytest_cache .tox MANIFEST build coverage.xml dist docs-build docs/man docs/reference htmlcov reg-settings.py

container-clean:		# Stop containers and remove Compose volumes and orphans
	$(COMPOSE) down --volumes --remove-orphans

help:					# List all make commands
	@awk -F ':.*#' '/^[a-zA-Z_-]+:.*?#/ { printf "\033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

kill:					# Force-stop and remove Compose containers
	$(COMPOSE) kill
	$(COMPOSE) rm --force

lint:					# Format and lint the code in the application container
	$(COMMAND_RUN) ./lint.sh

lint-check:				# Check formatting and lint without modifying files
	$(COMMAND_RUN) ./lint.sh --check

logs:					# Follow logs from all Compose services
	$(COMPOSE) logs --tail=100 --follow

restart: stop start		# Restart application containers in the background

run:					# Run the complete extraction script (use ARGS='--use-mirror')
	$(COMMAND_RUN) ./run.sh $(ARGS)

start:					# Start application containers in the background
	$(COMPOSE) up -d

stop:					# Stop application containers
	$(COMPOSE) down

tags:					# Generate a tags file (requires universal-ctags)
	@git ls-files | ctags -L - --tag-relative=yes --quiet --append -f "$(TAGS_FILE)"

test:					# Run pytest and show the coverage report (use TEST_ARGS='...')
	$(COMMAND_RUN) bash -c 'coverage run -m pytest $(TEST_ARGS) && coverage report'

tse:					# Run tse.py (use ARGS='candidatura --years=2024')
	$(COMMAND_RUN) python tse.py $(ARGS)
