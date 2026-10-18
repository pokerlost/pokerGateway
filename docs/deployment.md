# Gateway deployment

The gateway runtime image is non-root, read-only and uses an exec Traefik PID 1 with bounded shutdown. Its Docker context contains only reviewed proxy configuration. BuildKit's existing private repository cache is the primary backend when CI is connected; cache restoration does not replace fresh proxy tests. No external registry package is published until approved.

The Helm wrapper vendors the exact checksummed upstream chart rather than copying controller templates. It uses Gateway API v1 routes, existing TLS references outside explicit localDevelopment, ClusterIP services, namespaced route references and no application deployment rights. Controller/CRDs may be installed only in the specifically created disposable cluster. Ordinary application service accounts never obtain those controller rights. No Traefik Hub subscription, paid control plane or production certificate is configured.

Platform composition, image/route references, data-preserving shutdown and rollback belong to platformInfra. Local tests generate disposable TLS material and synthetic HTTP/WebSocket fixtures; those are not production endpoints or certificates. Preserve the previous tested image and values for rollback.
