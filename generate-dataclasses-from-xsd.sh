#!/bin/bash

set -o errexit -o nounset -o pipefail

poetry run xsdata generate dmarc-aggregate-report.xsd --package dmarc_metrics_exporter.model