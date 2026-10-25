# syntax=docker/dockerfile:1.27.1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
FROM traefik:v3.7.16@sha256:c8a121e4bb1347e8fd52657fab12f2cb70b68f8a018895e2068f92c9e519b9c2 AS runtime
ARG SOURCE_COMMIT
ARG APP_VERSION
COPY --exclude=traefik.yaml --chmod=u=rwX,go=rX config/ /etc/traefik/
COPY --chmod=0444 config/traefik.yaml /etc/pokerlost-compose.yaml
COPY --chmod=u=rwX,go=rX plugins/headerguard/ /plugins-local/src/github.com/pokerlost/headerguard/
COPY --chmod=0444 LICENSE THIRD_PARTY_NOTICES.md /licenses/
COPY --chmod=u=rwX,go=rX LICENSES/ /licenses/third-party/
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/pokerlost/pokerGateway"
LABEL org.opencontainers.image.revision=$SOURCE_COMMIT
LABEL org.opencontainers.image.version=$APP_VERSION
USER 65532:65532
EXPOSE 8080 8443
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 CMD ["traefik", "healthcheck", "--ping", "--ping.entrypoint=ping", "--entrypoints.ping.address=:8082"]
ENTRYPOINT ["traefik"]
CMD ["--configFile=/etc/pokerlost-compose.yaml"]
