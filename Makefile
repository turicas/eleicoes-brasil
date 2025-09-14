TAGS_FILE = .tags
.PHONY: clean help lint lint-check tags test

clean: 					# Clean temporary files
	rm -f $(TAGS_FILE)
	find -regex '.*\.pyc' -exec rm {} \;
	find -regex '.*~' -exec rm {} \;
	rm -rf reg-settings.py MANIFEST dist build *.egg-info rows.1 .tox
	rm -rf docs-build docs/reference docs/man $(TAGS_FILE)
	python -m coverage erase

help:					# List all make commands
	@awk -F ':.*#' '/^[a-zA-Z_-]+:.*?#/ { printf "\033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

lint:					# Run linter script
	./lint.sh

lint-check:				# Run the linter without changing files
	./lint.sh --check

tags:					# Generate tags file for the entire project (requires universal-ctags)
	@git ls-files | ctags -L - --tag-relative=yes --quiet --append -f "$(TAGS_FILE)"

test:					# Execute `pytest` and coverage report inside `web` container
	coverage run -m pytest $(TEST_ARGS) && coverage report
