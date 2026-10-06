.PHONY: install test demo app
install:
	pip install -e ".[dev]"
test:
	pytest -q
demo:
	PYTHONPATH=src python -m curve_monitor.cli --demo
app:
	streamlit run app.py
