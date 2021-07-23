# Build tools - venv must be initialised beforehand

SHELL := /bin/bash

.PHONY: check_virtualenv install test travis_test

travis_test:
	python -m flake8 -v --exclude=.idea,.git,venv
	python -m mypy imbibed.py
	python -m mypy --ignore-missing-imports daily_visualisation.py
		#FIXME: find a better fix for ' error: Cannot find module named 'svgwrite' '
	python -m mypy stock_check.py
	pylint -d R0801 imbibed.py daily_visualisation.py stock_check.py
	python tests.py

test: travis_test
	python -m isort -c .
	# isort behaves differently under travis, so don't run it there

check_virtualenv:
	pipenv --venv

install: check_virtualenv
	pipenv install