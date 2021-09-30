#!/usr/bin/env bash

source /venv/bin/activate

if [ -n "$CONFIGURATION_FILE" ]; then
  echo "Using configuration file: $CONFIGURATION_FILE"
  exec python -m dmarc_metrics_exporter --configuration "$CONFIGURATION_FILE"
else
  echo "CONFIGURATION_FILE is not set, using /etc/dmarc-metrics-exporter.json"
  exec python -m dmarc_metrics_exporter
fi
