# syntax=docker/dockerfile:1.27.1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
FROM traefik:v3.7.15@sha256:0f6150202bc1fed72a7bd2107460eaa510e5b8a905f3fdb5b84f2c8619c33368 AS runtime
ARG SOURCE_COMMIT
COPY --exclude=traefik.yaml --chmod=u=rwX,go=rX config/ /etc/traefik/
COPY --chmod=0444 config/traefik.yaml /etc/pokerlost-compose.yaml
COPY --chmod=u=rwX,go=rX plugins/headerguard/ /plugins-local/src/github.com/pokerlost/headerguard/
COPY --chmod=0444 LICENSE THIRD_PARTY_NOTICES.md /licenses/
COPY --chmod=u=rwX,go=rX LICENSES/ /licenses/third-party/
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/pokerlost/pokerGateway"
LABEL org.opencontainers.image.revision=$SOURCE_COMMIT
USER 65532:65532
EXPOSE 8080 8443
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 CMD ["traefik", "healthcheck", "--ping", "--ping.entrypoint=ping", "--entrypoints.ping.address=:8082"]
ENTRYPOINT ["traefik"]
CMD ["--configFile=/etc/pokerlost-compose.yaml"]
