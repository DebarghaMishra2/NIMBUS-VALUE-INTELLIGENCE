.PHONY: install run test evaluate
install:
	python -m pip install -r requirements-dev.txt
run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
test:
	pytest -q
evaluate:
	python -m evaluation.evaluate --dataset both
