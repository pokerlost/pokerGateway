# Gateway versions

`versions.lock.json` pins the upstream controller image, upstream chart checksum and Gateway API compatibility. The wrapper chart owns its own version in `deploy/chart/Chart.yaml`. The Python project version describes verification tooling, not a new reverse proxy implementation.

The header-routing wrapper candidate is `0.2.0-dev.0`; upstream Traefik remains `3.7.15`. No tag or release is created. Header-selection, TLS, forwarding and bridge asset policies are compatibility surfaces. An upstream patch still needs actual HTTP/TLS/WebSocket and disposable-Kubernetes acceptance before its digest is updated.

## Local verification and release readiness

`make version` reads the native version owners. `make ci-local` executes the
repository's native quality/build/acceptance targets once, then checks artifact
versions. No GitHub token or Actions API is required. Dependency preparation may
need the existing package/image access; `OFFLINE=1` requires prepared inputs and
fails as blocked when they are unavailable. BuildKit caches dependencies and build
layers, while tests execute freshly. `make coverage` reads the current result and
never reruns the suite. Coverage below 100% is advisory.

`coverage/ci-local.json` records schema 1, source commit/dirty/content SHA-256,
commands and exits, native tool versions, artifact hashes/versions and timestamps.
`coverage/ci-local-summary.md` and `coverage/artifacts.json` are supporting reports;
`coverage/summary.md` remains the coverage report. Ignored build outputs remain in
`dist/`. A source or lock change invalidates previous evidence. A failed or blocked
run must not leave a successful current receipt. Local CI does not replace hosted
mandatory checks or authorize a merge when those checks are billing-blocked.

Choose a version bump from the actual compatibility effect, update its native
metadata/lock/chart relationship and changelog, and run local CI on the exact
reviewed source. Quality/documentation-only work keeps current prerelease versions.
A clean integrated `main` with successful mandatory checks can receive an annotated
`v<application-version>` tag (or `chart/v<chart-version>` for an independent chart),
after inspecting tag-triggered workflows and confirming explicit task authority.
Tags, releases, package publication and deployment are separate operations; the
commands above do none of them. Never retag a published artifact or infer a registry
digest from a local Docker image ID.

The independently packaged wrapper uses `deploy/chart/Chart.yaml` version for its
chart and OCI label. `appVersion` is the pinned upstream Traefik version from
`versions.lock.json`; verification-only Python metadata is not the runtime version.
`make verify` executes real isolated HTTP/TLS/WebSocket fixtures. Traefik coverage
is not applicable and the bundled Go guard is not instrumented; report that limit
instead of a synthetic percentage. Native pytest JUnit reports are retained.

## Prepared offline acceptance

After an online full pass on the same clean source, `OFFLINE=1 make ci-local`
validates the saved source identity, runtime and fixture image IDs, and packaged
chart checksum in `coverage/gateway-cache.json`. It reuses those exact artifacts
without BuildKit or image pulls. Static/unit checks and actual HTTP/TLS/WebSocket
proxy acceptance still run freshly; synthetic containers use an internal network,
while host uv uses its prepared cache with `UV_OFFLINE=1`. Source changes, replaced
images, changed chart bytes and missing prepared inputs reject reuse. The receipt
remains separate from each fresh CI result; no image is published or relabelled.
