# pokerGateway

Traefik OSS is the platform reverse proxy. It routes the Vue site, its immutable Flutter bundle and existing foundation API prefixes; it never starts applications or owns game rules. No Docker socket or public dashboard is mounted. `platformInfra` owns Compose and Kubernetes composition.

Run `make install build test-unit test chart`. `make run` exposes only loopback high ports. Local HTTP is diagnostic; external deployment requires an existing TLS Secret and hostnames. The chart composes the pinned official Traefik controller with Gateway API routes. Version pins and upstream chart checksums are in `versions.lock.json`; Gateway API 1.6.3 matches Traefik's actual Go dependency. Chart 42.0.0 defaults to 3.7.14; this configuration explicitly selects 3.7.15 and requires actual disposable-Kind acceptance.

API prefix stripping is explicit: `/api/authService/getOpenApi` reaches `/getOpenApi`, without changing the application's operation IDs or inventing business routes. No production realtime upstream exists. WebSocket echo and round-robin targets are isolated test fixtures only. See [gateway behavior](docs/gateway.md) and [deployment](docs/deployment.md).

From this exact root, `make check` runs locked format/lint/types, eight declarative configuration
tests and Helm validation in Docker; `make coverage` reports notApplicable for the external
Traefik binary and declarative config. `make chart` packages the owner chart under
`coverage/chart/`. `make verify` freshly runs the five existing HTTP/TLS/WebSocket/failure/drain
scenarios against the canonical non-root read-only Traefik and synthetic fixture images.
Only that explicit test driver runs on host/CI with uv 0.12.15 to control the Docker CLI; no
application or test container receives the daemon socket or user HOME. Ordinary CI never
publishes. The separate owner/full-SHA manual delivery consumes a successful exact-SHA CI
candidate archive, checks the tested image identity, and writes only the approved private
package with SBOM/provenance. Merge, releases and production deployment remain separate.
