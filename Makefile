ifeq ($(CONTAINERIZED),1)
RUFF ?= ruff
else
RUFF ?= uvx --from ruff==0.16.4 ruff
endif
# Quick dev commands never prepare a product/build image.
ifneq ($(filter lint format format-check check,$(MAKECMDGOALS)),)
override CONTAINERIZED := 1
endif
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
QUALITY_RUN_ARGS += --pull=never
UV ?= uv
QUALITY_EXTRA_TARGETS := chart-check
ONLINE_BUILD_COMMAND = $(DOCKER) buildx build $(DOCKER_BUILD_ARGS) $(LOCAL_BUILD_NETWORK) --output type=docker,rewrite-timestamp=true --tag $(RUNTIME_IMAGE) .
COVERAGE_COMMAND = sh -ec 'printf "%s\n" "Coverage: external Traefik and declarative configuration notApplicable; bundled Go guard and Python metadata tooling notMeasured (executed by native tests, without coverage instrumentation)." | tee coverage/summary.md'
VERIFY_COMMAND = GATEWAY_TEST_IMAGE=$(RUNTIME_IMAGE) $(MAKE) CONTAINERIZED=1 test && $(DOCKER) image inspect $(RUNTIME_IMAGE) --format '{{.Id}}' > coverage/tested-image-id.txt && git rev-parse HEAD > coverage/source-commit.txt
ifeq ($(OFFLINE),1)
BUILD_COMMAND = $(RELEASE_CHECK_COMMAND)
IMAGE_COMMAND = $(MAKE) gateway-offline-preflight
else
BUILD_COMMAND = $(ONLINE_BUILD_COMMAND)
IMAGE_COMMAND = $(ONLINE_BUILD_COMMAND)
endif
BUILD_RECEIPT_COMMAND := true
VERSION_COMMAND = $(QUALITY_RUN) python -m docker.project_metadata version
CACHE_METADATA_COMMAND = $(DOCKER) image inspect $(RUNTIME_IMAGE) > coverage/runtime-image.json && $(DOCKER) image inspect pokergateway:fixture --format '{{.Id}}' > coverage/fixture-image-id.txt
ifeq ($(OFFLINE),1)
RELEASE_CHECK_COMMAND = $(CACHE_METADATA_COMMAND) && $(QUALITY_RUN) python -m docker.project_metadata check-offline
else
RELEASE_CHECK_COMMAND = $(CACHE_METADATA_COMMAND) && $(QUALITY_RUN) python -m docker.project_metadata capture-offline
endif
RECEIPT_COMMAND = $(QUALITY_RUN) python docker/release.py receipt
OFFLINE_PREFLIGHT_COMMAND = $(MAKE) gateway-offline-preflight
CI_LOCAL_TARGETS := acceptance coverage build chart verify release-check
QUALITY_EXTRA_TARGETS += acceptance
CI_LOCAL_TARGETS ?= acceptance coverage build verify release-check
include docker/quality-python.mk
.PHONY: gateway-offline-preflight
gateway-offline-preflight: source-identity
	$(CACHE_METADATA_COMMAND)
	$(QUALITY_RUN) python -m docker.project_metadata check-offline

.PHONY: native-prerequisites
help: native-prerequisites
native-prerequisites:
	@printf '%s\n' 'Gateway proxy acceptance also requires host uv 0.12.15; Docker owns the pinned runtime and fixture images.'
.PHONY: build-metadata
build-metadata:
	@printf '%s\n' 'APP_VERSION=$(APP_VERSION)' 'SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH)'

.PHONY: fixture-image chart
fixture-image:
ifeq ($(OFFLINE),1)
	$(MAKE) gateway-offline-preflight
else
	$(DOCKER) buildx build --file tests/Dockerfile $(DOCKER_BUILD_ARGS) $(LOCAL_BUILD_NETWORK) --load --tag pokergateway:fixture .
endif
ifeq ($(OFFLINE),1)
verify: gateway-offline-preflight
else
verify: image fixture-image
endif
chart: quality-image
ifeq ($(OFFLINE),1)
	$(RELEASE_CHECK_COMMAND)
else
	@mkdir -p dist
	$(QUALITY_RUN) make chart OUTPUT_DIR=/app/coverage/chart
endif

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
	$(RUFF) check tests docker/project_metadata.py
	$(RUFF) format --check tests docker/project_metadata.py
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
	$(UV) run --locked pytest tests/test_configuration.py tests/test_metadata.py --junitxml=coverage/configuration.xml
test:
	$(UV) run --locked --python 3.14.7 pytest tests/test_proxy.py --junitxml=coverage/proxy.xml
check: lint ## Fast lint-only gate; no tests/build.

acceptance: lint typecheck test-unit chart-check
run:
	$(DOCKER) compose --project-name poker-gateway-local up --detach --wait --wait-timeout 60

endif

.PHONY: dev-policy-help
help: dev-policy-help
dev-policy-help:
	@printf '%s\n' 'Daily: make lint; explicit git push origin dev.' \
	  'Manual only: test, typecheck, coverage, build, acceptance, ci-local.' \
	  'Native lint tools must be installed; lint never syncs/builds the application.'
