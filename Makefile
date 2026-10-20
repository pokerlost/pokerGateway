ifeq ($(OFFLINE),1)
export UV_OFFLINE := 1
endif
APP_VERSION = $(shell sed -n 's/^version: //p' deploy/chart/Chart.yaml)
SOURCE_COMMIT = $(shell git rev-parse HEAD)
SOURCE_DATE_EPOCH = $(shell git log -1 --pretty=%ct)
override DOCKER_BUILD_ARGS += --build-arg SOURCE_COMMIT=$(SOURCE_COMMIT) --build-arg APP_VERSION=$(APP_VERSION) --build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH)
ifneq ($(CONTAINERIZED),1)
QUALITY_DIST_MOUNT = --mount "type=bind,source=$(CURDIR)/dist,target=/app/dist,readonly"
QUALITY_IMAGE := pokergateway:quality
RUNTIME_IMAGE := pokergateway:candidate
QUALITY_TEST := test-unit
UV ?= uv
QUALITY_EXTRA_TARGETS := chart-check
BUILD_COMMAND = $(DOCKER) buildx build $(DOCKER_BUILD_ARGS) $(LOCAL_BUILD_NETWORK) --output type=docker,rewrite-timestamp=true --tag $(RUNTIME_IMAGE) .
COVERAGE_COMMAND = sh -ec 'printf "%s\n" "Coverage: external Traefik and declarative configuration notApplicable; bundled Go guard notMeasured (executed by real Yaegi proxy tests, no instrumented Go coverage)." | tee coverage/summary.md'
VERIFY_COMMAND = GATEWAY_TEST_IMAGE=$(RUNTIME_IMAGE) $(MAKE) CONTAINERIZED=1 test && $(DOCKER) image inspect $(RUNTIME_IMAGE) --format '{{.Id}}' > coverage/tested-image-id.txt && git rev-parse HEAD > coverage/source-commit.txt
IMAGE_COMMAND = $(DOCKER) buildx build $(DOCKER_BUILD_ARGS) $(LOCAL_BUILD_NETWORK) --output type=docker,rewrite-timestamp=true --tag $(RUNTIME_IMAGE) .
BUILD_RECEIPT_COMMAND := true
VERSION_COMMAND = $(QUALITY_RUN) python docker/project_metadata.py version
RELEASE_CHECK_COMMAND = $(DOCKER) image inspect $(RUNTIME_IMAGE) > coverage/runtime-image.json && $(QUALITY_RUN) python docker/project_metadata.py release-check
RECEIPT_COMMAND = $(QUALITY_RUN) python docker/release.py receipt
OFFLINE_PREFLIGHT_COMMAND = $(DOCKER) image inspect pokergateway:fixture traefik:v3.7.15@sha256:0f6150202bc1fed72a7bd2107460eaa510e5b8a905f3fdb5b84f2c8619c33368 >/dev/null || { echo "BLOCKED: prepare pinned Traefik and fixture images online first." >&2; exit 2; }
CI_LOCAL_TARGETS := check coverage build chart verify release-check
include docker/quality-python.mk
.PHONY: build-metadata
build-metadata:
	@printf '%s\n' 'APP_VERSION=$(APP_VERSION)' 'SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH)'

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
	$(UV) run --locked ruff check tests docker/project_metadata.py
	$(UV) run --locked ruff format --check tests docker/project_metadata.py
typecheck:
	$(UV) run --locked mypy tests docker/project_metadata.py
build:
	$(DOCKER) buildx build --load --tag pokergateway:candidate .
chart-check:
	$(HELM) lint deploy/chart --strict --set localDevelopment=true --set traefik.image.repository=pokergateway --set traefik.image.tag=validation-only
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
