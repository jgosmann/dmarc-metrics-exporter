#!/bin/bash

set -o errexit -o nounset -o pipefail

poetry run xsdata generate dmarc-aggregate-report-0.1.xsd --package dmarc_metrics_exporter.model.dmarc_0_1
poetry run xsdata generate dmarc-aggregate-report-2.0.xsd --package dmarc_metrics_exporter.model.dmarc_2_0
