# HTTP service routing

Traefik is the sole API service selector. Nginx serves static Vue/Flutter assets and never
proxies API traffic. Environment upstreams belong to platformInfra; the SDK owns the exact
case-sensitive `ServiceId` catalog. HTTP field names are case-insensitive.

Clients send `x-pokerlost-serviceId` with `/<lowerCamelCaseOperation>` and the original body.
Native exact Header matchers select named fixed load balancers. No header becomes a URL or DNS
name. A small bundled Go middleware fills the native matcher's missing boundary: it checks the
number of field values before upstream I/O, preventing first-value/last-value ambiguity.
It uses Traefik's supported local-plugin mechanism, no downloaded plugin or extra network service.
The middleware performs no service selection, authorization or retries.

| Input | Status | Envelope error |
| --- | --- | --- |
| Missing header | 400 | POKERLOST_SERVICE_ID_REQUIRED |
| Empty, duplicate, comma-combined or malformed value | 400 | POKERLOST_SERVICE_ID_INVALID |
| Unregistered or wrong-case value | 404 | POKERLOST_SERVICE_ID_UNKNOWN |
| Legacy prefix (including normalized encoding), internal probe/metrics | 404 | POKERLOST_ROUTE_NOT_FOUND |
| Allowed backend unavailable | 502/503 | Traefik upstream failure; never another service |

Backends still own 401/403/405, scopes, audience and response headers. There is no default
cross-origin policy: the website and HTTP API are same-origin. Cross-origin preflights get no
CORS grant and never invoke an API. Native browser WebSocket cannot send this custom header;
production realtime remains planned. Isolated existing WS fixtures only test proxy transport.

The boundary accepts one bounded validated X-Request-ID or generates a random replacement,
forwards it and returns it. IDs and service values are not credentials. Logs omit query strings,
bodies, authorization and cookies; request_id is a JSON field, never a metrics/Loki stream label.
`/metrics` and `/ping` use an internal entrypoint with no public listener.

Local plugins are an experimental upstream extension point. Package the reviewed source in the
gateway image and test the real image. A missing/failed plugin must make the routers unavailable,
never bypass validation. Prepared remote rollout requires its separately authorized target.

## Configuration ownership

The exact ServiceId catalog is SDK-owned at main c4d8327e8318eab6769b3f05c4a7d848c75afb0b. Gateway rules contain only reviewed exact registered identities; the Go guard never selects destinations. platformInfra owns environment upstream URLs and mounts one validated `upstreams.yaml`. The packaged default has empty server lists: a configured but unprovided target returns 503, with no inferred URL or fallback. Helm receives fixed Kubernetes service names through the same platform owner. Bare upstream Traefik images do not contain the guard; use the verified bundled gateway image.
