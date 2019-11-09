# Build tools - venv must be initialised beforehand

SHELL := /bin/bash

.PHONY: check_virtualenv test

test:
	python -m flake8 -v --exclude=.idea,.git,venv
	python -m isort -c
	python -m mypy imbibed.py
	python -m mypy --ignore-missing-imports daily_visualisation.py
		#FIXME: find a better fix for ' error: Cannot find module named 'svgwrite' '
	python -m mypy stock_check.py

check_virtualenv:
	pipenv --venv