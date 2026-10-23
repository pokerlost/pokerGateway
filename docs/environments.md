# Gateway environment boundaries

The gateway routes the fixed `x-pokerlost-serviceId` allowlist; environment names do
not select arbitrary upstreams and do not grant authentication. The SDK/clients
select an explicit `main`, `dev`, `test` or `local` origin before sending a request.
Missing remote endpoints are not configured; no DNS name or remote deployment is
supplied by this repository. TLS is required outside caller loopback.

Existing Compose is the local contour. Its container service names are an internal
fixed routing map, not a license to allow arbitrary HTTP hosts in the SDK. A host
client uses the explicit loopback-published gateway port. A container client needs
a reviewed mapping/TLS endpoint; do not silently substitute the host's loopback.

Before a separately authorized remote deployment, use distinct namespaces such as
`pokerlost-dev` and `pokerlost-test`, distinct origins and secrets, and set
`traefik.providers.kubernetesCRD.namespaces` to that exact namespace. Preserve
`allowCrossNamespace: false`, service selectors and the existing allowlist. Current
chart defaults still describe the prior local foundation; a source identity field
does not migrate resources. platformInfra owns composition and blocks non-local
Compose execution. No running stack, data or credentials change in this source update.

Use `make lint` before explicit `git push origin dev`. HTTP, WebSocket, TLS, Helm
and cluster verification stay manual. The verification-tools version is separate
from the gateway wrapper chart and the pinned upstream Traefik version.
