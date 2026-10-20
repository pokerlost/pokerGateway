# Gateway deployment

The gateway runtime image is non-root, read-only and uses an exec Traefik PID 1 with bounded shutdown. Its Docker context contains only reviewed proxy configuration and the bundled metadata guard. BuildKit's existing private repository cache is the primary backend when CI is connected; cache restoration does not replace fresh proxy tests. No external registry package is published until approved.

The Helm wrapper vendors the exact checksummed upstream chart rather than copying controller templates. It uses Gateway API v1 routes, existing TLS references outside explicit localDevelopment, ClusterIP services, namespaced route references and no application deployment rights. Controller/CRDs may be installed only in the specifically created disposable cluster. Ordinary application service accounts never obtain those controller rights. No Traefik Hub subscription, paid control plane or production certificate is configured.

Platform composition, image/route references, data-preserving shutdown and rollback belong to platformInfra. Local tests generate disposable TLS material and synthetic HTTP/WebSocket fixtures; those are not production endpoints or certificates. Preserve the previous tested image and values for rollback.

The chart installs the controller default TLSOption with TLS 1.3 minimum and strict SNI, matching the file-provider runtime. Deploy one default TLSOption per controller; this platform owns one gateway controller scoped to its namespace. HTTPS requires an explicit hostname and existing certificate Secret. Verify the issuing CA and SNI; never bypass certificate validation.

Development OCI publication requires the exact full `GATEWAY_IMAGE_REVIEWED_SHA` repository variable and successful fresh proxy tests from the same run. Publication is restricted to the approved private `ghcr.io/pokerlost/pokergateway` package, checks the tested runtime configuration identity, and emits SBOM/provenance. No release or deployment is triggered.

CI exports an attested OCI archive from the same workspace/cache after real tests and
requires its configuration ID to match the tested Docker image. Delivery checks source/run,
archive SHA-256 and the existing private package, then uses checksum-pinned official ORAS
to copy the complete index by digest. SBOM/provenance remain index children. The publisher
does not rebuild. Native registry readback requires the same root digest and tested image
ID. BuildKit remains the build cache; an archive is a ready artifact, not another cache.

## Header routing image

Wrapper chart 0.2.0-dev.0 requires the same bundled gateway image used by file-provider acceptance, never the bare upstream image. The upstream base remains pinned in Dockerfile/versions.lock.json. platformInfra supplies its actual verified image tag/digest; versionOverride records the real Traefik binary version independently of the application image tag. Local plugin loading aborts on failure. No hostPath or downloaded remote plugin is used. Header guards validate ambiguity; native Header/HTTPRoute matching alone selects fixed named upstreams. Real Compose proxy acceptance and rendered Helm validation are separate from disposable-Kind acceptance.

## Native configuration modes

The image default command explicitly selects `/etc/pokerlost-compose.yaml` for
file-provider local Compose. That file is outside Traefik's automatic config search
path. Native Helm Pod args replace the image CMD and enable only Kubernetes
providers/listeners; an auto-discovered Compose config must not shadow those args.
Both modes load the same bundled guard. Static v3 matchers use one path per matcher
joined by OR, verified through real HTTP rather than only YAML parsing.

## Reproducible image identity

Native Make and Actions builds pin `SOURCE_DATE_EPOCH` to the exact source commit timestamp, using [BuildKit's supported reproducible-build input](https://docs.docker.com/build/ci/github-actions/reproducible-builds/). Wall-clock creation metadata must not change a tested configuration during private promotion. The strict tested image-ID comparison remains required; a cache hit alone is insufficient.

Both Docker and OCI runtime exporters enable BuildKit rewrite-timestamp=true. SOURCE_DATE_EPOCH alone stabilizes creation metadata but does not ensure identical COPY layer metadata between fresh checkouts; strict pre/post-push image-ID checks remain in place.

## Exact OCI promotion

After tests, the same CI workspace exports runtime-image.oci.tar with SBOM/provenance and checks its config ID against the tested image. Delivery verifies its checksum and copies the complete OCI graph with official checksum-pinned ORAS 1.3.5. It requires an existing private destination before push and checks digest/config identity afterward. No new package, ACL, release or deployment is created implicitly.
