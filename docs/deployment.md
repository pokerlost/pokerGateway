# Gateway deployment

The gateway runtime image is non-root, read-only and uses an exec Traefik PID 1 with bounded shutdown. Its Docker context contains only reviewed proxy configuration. BuildKit's existing private repository cache is the primary backend when CI is connected; cache restoration does not replace fresh proxy tests. No external registry package is published until approved.

The Helm wrapper vendors the exact checksummed upstream chart rather than copying controller templates. It uses Gateway API v1 routes, existing TLS references outside explicit localDevelopment, ClusterIP services, namespaced route references and no application deployment rights. Controller/CRDs may be installed only in the specifically created disposable cluster. Ordinary application service accounts never obtain those controller rights. No Traefik Hub subscription, paid control plane or production certificate is configured.

Platform composition, image/route references, data-preserving shutdown and rollback belong to platformInfra. Local tests generate disposable TLS material and synthetic HTTP/WebSocket fixtures; those are not production endpoints or certificates. Preserve the previous tested image and values for rollback.

The chart installs the controller default TLSOption with TLS 1.3 minimum and strict SNI, matching the file-provider runtime. Deploy one default TLSOption per controller; this platform owns one gateway controller scoped to its namespace. HTTPS requires an explicit hostname and existing certificate Secret. Verify the issuing CA and SNI; never bypass certificate validation.

Development OCI publication requires the exact full `GATEWAY_IMAGE_REVIEWED_SHA` repository variable and successful fresh proxy tests from the same run. Publication is restricted to the approved private `ghcr.io/pokerlost/pokergateway` package, checks the tested runtime configuration identity, and emits SBOM/provenance. No release or deployment is triggered.
