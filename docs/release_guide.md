# Candidate delivery

Run locked lint/types, routing/security contracts, Helm lint/package and fresh real HTTP/TLS/WebSocket/upstream-failure/drain tests. Validate the pinned upstream artifact checksums and runtime filesystem/socket policy. Kubernetes acceptance belongs to the reviewed platformInfra composition and must be reported separately from Helm rendering.

A candidate container may be published only to the approved private destination for a reviewed full commit. Preserve SBOM/provenance, image digest, chart checksum and verification reports. Submit the resulting artifact reference through platformInfra's PR. No tag, release, merge, live migration or production deployment is authorized by this procedure. Rollback selects the prior compatible gateway/chart digest pair.
