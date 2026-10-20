# Third-party notices

Original repository source and documentation use [MIT](LICENSE).

The Traefik OSS binary/image retains its upstream MIT and dependency notices.
The unmodified vendored traefik-42.0.0.tgz chart retains traefik/LICENSE (Apache-2.0),
also copied to LICENSES/traefik-chart-Apache-2.0.txt. The header guard is original source.
The wrapper chart's MIT license applies to its original configuration; nested
upstream files retain their notices. No Docker provider/socket or proprietary
Traefik Hub component is enabled. Go/Python/Helm build tools retain upstream terms.

The CI-only [ORAS CLI 1.3.5](https://github.com/oras-project/oras/tree/v1.3.5) and official setup action use Apache-2.0. The CLI is checksum-verified in the runner tool cache and is not included in the runtime image. Preserve its upstream license if redistributing that tool.
