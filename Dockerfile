FROM python:3

# adduser and directories
RUN adduser --system --group --uid 1000 dmarc-metrics && \
    mkdir /var/lib/dmarc-metrics-exporter && \
    chown dmarc-metrics:dmarc-metrics /var/lib/dmarc-metrics-exporter

# install python package
RUN pip3 install dmarc-metrics-exporter

# configuration file will be linked into container on runtime
# -v {your path}/dmarc-metrics-exporter.json:/etc/dmarc-metrics-exporter.json

EXPOSE 9797

ENTRYPOINT ["dmarc-metrics", "python3", "-m", "dmarc_metrics_exporter"]
