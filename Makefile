override DOCKER_BUILD_ARGS += --build-arg SOURCE_COMMIT=$(shell git rev-parse HEAD)
ifneq ($(CONTAINERIZED),1)
QUALITY_IMAGE := pokergateway:quality
RUNTIME_IMAGE := pokergateway:candidate
QUALITY_TEST := test-unit
UV ?= uv
QUALITY_EXTRA_TARGETS := chart-check
BUILD_COMMAND = $(DOCKER) buildx build $(DOCKER_BUILD_ARGS) --load --tag $(RUNTIME_IMAGE) .
COVERAGE_COMMAND = sh -ec 'printf "%s\n" "Coverage: notApplicable for declarative Traefik configuration; the external Traefik binary is not instrumented by this repository." | tee coverage/summary.md'
VERIFY_COMMAND = $(MAKE) CONTAINERIZED=1 test && $(DOCKER) image inspect $(RUNTIME_IMAGE) --format '{{.Id}}' > coverage/tested-image-id.txt && git rev-parse HEAD > coverage/source-commit.txt
IMAGE_COMMAND = $(DOCKER) buildx build $(DOCKER_BUILD_ARGS) --load --tag $(RUNTIME_IMAGE) .
include docker/quality-python.mk
.PHONY: fixture-image chart
fixture-image:
	$(DOCKER) buildx build --file tests/Dockerfile $(DOCKER_BUILD_ARGS) --load --tag pokergateway:fixture .
verify: image fixture-image
chart: quality-image
	@mkdir -p dist
	$(QUALITY_RUN) make chart OUTPUT_DIR=/app/coverage/chart

else
.DEFAULT_GOAL := help
DOCKER ?= docker
HELM ?= helm
UV ?= uv
.PHONY: help install lint typecheck test-unit test check build chart run
help:
	@echo "install lint typecheck test check build chart run"
install:
	$(UV) sync --locked --group fixture
lint:
	$(UV) run --locked ruff check tests
	$(UV) run --locked ruff format --check tests
typecheck:
	$(UV) run --locked mypy tests
build:
	$(DOCKER) buildx build --load --tag pokergateway:candidate .
chart-check:
	$(HELM) lint deploy/chart --strict --set localDevelopment=true
OUTPUT_DIR ?= dist
chart: chart-check
	$(HELM) package deploy/chart --destination $(OUTPUT_DIR)
test-unit:
	$(UV) run --locked pytest tests/test_configuration.py --junitxml=coverage/configuration.xml
test:
	$(UV) run --locked --python 3.14.7 pytest tests/test_proxy.py --junitxml=coverage/proxy.xml
check: lint typecheck test-unit chart-check
run:
	$(DOCKER) compose --project-name poker-gateway-local up --detach --wait --wait-timeout 60

endif
