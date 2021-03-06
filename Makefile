VERSION=$(shell python -c "import financeager; print(financeager.__version__)")

.PHONY: all test install upload tag publish coverage lint format style-check

all:
	@echo "Available targets: install, test, upload, tag, publish, coverage, lint, format, style-check"

install:
	pip install -U -e .

test:
	python setup.py test

upload: README.md setup.py
	rm -f dist/*
	python setup.py bdist_wheel --universal
	twine upload dist/*

tag:
	git tag v$(VERSION)
	git push --tags origin master
	hub release create -m v$(VERSION) -m "$$(awk -v RS='' '/\[v$(VERSION)\]/' Changelog.md | tail -n+2)" v$(VERSION)

publish: tag upload

coverage:
	coverage erase
	coverage run --source financeager setup.py test
	coverage report
	coverage html

lint:
	pre-commit run --all-files flake8

format:
	pre-commit run --all-files yapf
	pre-commit run --all-files end-of-file-fixer
	pre-commit run --all-files trailing-whitespace

style-check: format lint
