# pokerGateway

Read selected [baseRules](https://raw.githubusercontent.com/serrja/baseRules/730418d3cc480b4f05b88b4c8275296c4845a75a/docs/engineering.md), then [Pokerlost norms](https://raw.githubusercontent.com/pokerlost/projectRules/4785546cffa58f7ae1c22b6d6b8846a0141793eb/docs/project.md) before the local contract below.
These full-SHA links are reading sources, not automatic loaders or grants. Review
the source diff, update the explicit pin and run docs checks for a rules refresh.
Local overrides apply only to this repository's stated ownership boundary.

Traefik OSS owns the reverse proxy data plane. Compose/Helm own orchestration in platformInfra. No Docker socket, application launch endpoint, business logic, public dashboard or blanket mutation retry. Test actual HTTP/WebSocket/TLS routing with isolated synthetic fixtures. Preserve user metadata. No remote creation, OCI publication, merge/release or external deployment without task approval.
