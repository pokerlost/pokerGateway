# pokerGateway

Read selected [baseRules](https://raw.githubusercontent.com/serrja/baseRules/bafcb63ed94b9769a0ca098e5db4b33c55dbc1b9/docs/engineering.md), then [Pokerlost norms](https://raw.githubusercontent.com/pokerlost/projectRules/904c65a3daab88802fb5e414cdaccc7ad2b555a8/docs/project.md) before the local contract below.
These full-SHA links are reading sources, not automatic loaders or grants. Review
the source diff, update the explicit pin and run docs checks for a rules refresh.
Local overrides apply only to this repository's stated ownership boundary.

Traefik OSS owns the reverse proxy data plane. Compose/Helm own orchestration in platformInfra. No Docker socket, application launch endpoint, business logic, public dashboard or blanket mutation retry. Test actual HTTP/WebSocket/TLS routing with isolated synthetic fixtures. Preserve user metadata. No remote creation, OCI publication, merge/release or external deployment without task approval.

Daily work uses `dev` and lint only. `main` and `test` stay unchanged until an
explicit promotion. Full acceptance, template render/update checks, builds and
releases are manual; a dev snapshot is not a verified release.
