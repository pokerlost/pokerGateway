# Gateway behavior

Local file provider uses Compose DNS. The only listeners exposed by Compose are loopback high ports; ping remains internal. Proxy headers are not trusted from arbitrary peers. Request bodies are limited to 1 MiB, read/header waits are bounded, and WebSocket connections use the standard Traefik upgrade path. There is no blanket retry middleware.

Access logs drop all request/response headers and never capture bodies. Client-provided request IDs are removed before a backend; the backend owns server-generated IDs. Authorization headers required by an implemented backend are preserved in transit and omitted from logs. Unknown API/realtime paths are rejected instead of serving SPA HTML.

Same-origin Vue/Flutter embedding uses a CSP compatible with the actual local CanvasKit/Wasm assets. `wasm-unsafe-eval` permits WebAssembly compilation; JavaScript `unsafe-eval` and wildcard sources are absent. Inline styles are required by the Flutter renderer and are browser-tested. No cross-origin auth or iframe isolation is introduced.

Stateless HTTP can balance across upstream instances. One WebSocket stays on one upstream; reconnect/table ownership is not supplied by sticky sessions. Game authority and financial consistency remain outside the gateway.

The real fixture suite also checks loss of one upstream, no replay/failover retry, and SIGTERM during a controlled in-flight HTTP request. The request must complete and Traefik must exit within the configured grace period without OOM. These fixtures are verification code, never product endpoints. Traefik's third-party source is not reported as owned Python coverage.
