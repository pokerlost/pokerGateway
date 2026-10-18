.DEFAULT_GOAL := help
DOCKER ?= docker
HELM ?= helm
UV ?= uv
.PHONY: help install lint typecheck test-unit test check build chart run
help:
	@echo "install lint typecheck test check build chart run"
install:
	$(UV) sync --locked
lint:
	$(UV) run --locked ruff check tests
	$(UV) run --locked ruff format --check tests
typecheck:
	$(UV) run --locked mypy tests
build:
	$(DOCKER) buildx build --load --tag pokergateway:candidate .
chart:
	$(HELM) lint deploy/chart --strict --set localDevelopment=true
	$(HELM) package deploy/chart --destination dist
test-unit:
	$(UV) run --locked pytest tests/test_configuration.py
test:
	$(UV) run --locked pytest tests/test_proxy.py
check: lint typecheck test-unit chart test
run:
	$(DOCKER) compose --project-name poker-gateway-local up --detach --wait --wait-timeout 60
