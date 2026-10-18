# syntax=docker/dockerfile:1.27.1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
FROM ghcr.io/astral-sh/uv:0.12.15@sha256:62f8c047d0a0e9ece6b53fc63df902585a67a47a7f318ddec4a37db586edc8e3 AS uv
FROM python:3.14.7-slim-trixie@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /fixture
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=pokergateway-fixture-uv,target=/root/.cache/uv,sharing=locked uv sync --locked --no-dev --group fixture
COPY --chmod=0444 tests/echo_server.py /fixture/echo_server.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65532:65532
CMD ["/fixture/.venv/bin/python", "echo_server.py"]
