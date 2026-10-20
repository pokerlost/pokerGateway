# Gateway versions

`versions.lock.json` pins the upstream controller image, upstream chart checksum and Gateway API compatibility. The wrapper chart owns its own version in `deploy/chart/Chart.yaml`. The Python project version describes verification tooling, not a new reverse proxy implementation.

The header-routing wrapper candidate is `0.2.0-dev.0`; upstream Traefik remains `3.7.15`. No tag or release is created. Header-selection, TLS, forwarding and bridge asset policies are compatibility surfaces. An upstream patch still needs actual HTTP/TLS/WebSocket and disposable-Kubernetes acceptance before its digest is updated.
