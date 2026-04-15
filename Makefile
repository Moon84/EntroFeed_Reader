.PHONY: install
install:
	cd frontend && npm install
	uv pip install -e .

.PHONY: install-ci
install-ci:
	cd frontend && npm install
	uv pip install .

.PHONY: run
run:
	uvicorn src.app:app --reload --log-level debug --port 8001

.PHONY: run-ci
run-ci:
	uvicorn src.app:app &

.PHONY: dev-frontend
dev-frontend:
	cd frontend && npm run dev

.PHONY: dev-backend
dev-backend:
	uvicorn src.app:app --reload --log-level debug --port 8001

.PHONY: dev
dev:
	cd frontend && npm install
	pre-commit install

.PHONY: build
build:
	docker compose up --build

.PHONY: docker-up
docker-up:
	docker compose up -d

.PHONY: docker-down
docker-down:
	docker compose down

.PHONY: docker-restart
docker-restart:
	docker compose restart

.PHONY: docker-logs
docker-logs:
	docker compose logs -f

.PHONY: docker-rebuild
docker-rebuild:
	docker compose down
	docker compose up --build -d

.PHONY: clean
clean:
	rm -r ${DATA_DIR}

.PHONY: unit-test
unit-test:
	pytest -vvv -cov
