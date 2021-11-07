FROM python:3.7-slim AS builder
ARG version

# install python package in venv
RUN python3 -m venv venv && \
    venv/bin/pip3 --disable-pip-version-check install dmarc-metrics-exporter==${version}

FROM python:3.7-alpine AS runner

# adduser and directories
RUN addgroup --system --gid 1000 dmarc-metrics && \
    adduser --system --uid 1000 dmarc-metrics
USER dmarc-metrics

# copy pre-installed venv
COPY --from=builder /venv /venv

# configuration file will be linked into container on runtime
# -v {your path}/dmarc-metrics-exporter.json:/etc/dmarc-metrics-exporter.json

EXPOSE 9797

ENTRYPOINT ["/venv/bin/python3", "-m", "dmarc_metrics_exporter"]
