# pokerGateway

Traefik OSS is the platform reverse proxy. It routes the Vue site, its immutable Flutter bundle and existing foundation HTTP APIs by an explicit service header; it never starts applications or owns game rules. No Docker socket or public dashboard is mounted. `platformInfra` owns Compose and Kubernetes composition.

Run `make install build test-unit test chart`. `make run` exposes only loopback high ports. Local HTTP is diagnostic; external deployment requires an existing TLS Secret and hostnames. The chart uses the same gateway image: pinned official Traefik plus the bundled metadata guard, with native Gateway API routes. Version pins and upstream chart checksums are in `versions.lock.json`; Gateway API 1.6.3 matches Traefik's actual Go dependency. Chart 42.0.0 defaults to 3.7.14; this configuration explicitly selects 3.7.15 and requires actual disposable-Kind acceptance.

HTTP calls use a single operation path and canonical `x-pokerlost-serviceId` with an exact SDK-owned value. Legacy prefixes are rejected. [Header contract and error table](docs/header-routing.md) describe duplicate rejection, safe IDs and same-origin policy. No production realtime upstream exists. WebSocket echo and round-robin targets are isolated test fixtures only. See [gateway behavior](docs/gateway.md) and [deployment](docs/deployment.md).

From this exact root, `make check` runs locked format/lint/types, declarative configuration
tests and Helm validation in Docker; `make coverage` reports notApplicable for the external
Traefik binary and declarative config, with bundled Go adapter coverage explicitly notMeasured. `make chart` packages the owner chart under
`coverage/chart/`. `make verify` freshly runs the HTTP/1.1/HTTP/2/TLS/WebSocket/auth/failure/drain
scenarios against the canonical non-root read-only Traefik and synthetic fixture images.
Only that explicit test driver runs on host/CI with uv 0.12.15 to control the Docker CLI; no
application or test container receives the daemon socket or user HOME. Ordinary CI never
publishes. The separate owner/full-SHA manual delivery consumes a successful exact-SHA CI
candidate archive, checks the tested image identity, and writes only the approved private
package with SBOM/provenance. Merge, releases and production deployment remain separate.

Run `make help` for native tasks, `make version` for canonical artifact versions,
and `make ci-local` for the local required checks and `coverage/ci-local.json`.
`make release-check` validates built artifact identity; it does not publish or tag.
See [version and release policy](docs/versioning.md).

## 📄 License

Original source/documentation uses [MIT](LICENSE). Preserve the
[third-party notices](THIRD_PARTY_NOTICES.md); upstream assets, distributions and
private data retain their own terms and access boundaries.
