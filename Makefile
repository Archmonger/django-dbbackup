.PHONY: all test clean docs build upload install lint format

clean:
	find . -name "*.pyc" -type f -delete
	find . -name "__pycache__" -type d -exec rm -rf {} \;
	find . -name "*.egg-info" -type d -exec rm -rf {} \; || true
	rm -rf build/ dist/ \
	       coverage_html_report .coverage \
	       *.egg

test:
	hatch test

functional:
	hatch run functional:test

lint:
	hatch run lint:check

format:
	hatch run lint:format

format-check:
	hatch run lint:format-check

install:
	hatch build

build:
	hatch build

docs:
	hatch run docs:build

upload:
	make clean
	hatch build
	hatch publish
