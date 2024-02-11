import dataclasses

import aiohttp
import pytest
from prometheus_client.parser import text_string_to_metric_families
from prometheus_client.samples import Sample

import dmarc_metrics_exporter
from dmarc_metrics_exporter.dmarc_event import Disposition, Meta
from dmarc_metrics_exporter.dmarc_metrics import (
    DmarcMetrics,
    DmarcMetricsCollection,
    InvalidMeta,
)
from dmarc_metrics_exporter.prometheus_exporter import PrometheusExporter


@pytest.mark.asyncio
async def test_prometheus_exporter():
    metrics = DmarcMetricsCollection(
        metrics={
            Meta(
                reporter="google.com",
                from_domain="mydomain.de",
                dkim_domain="sub.mydomain.de",
                spf_domain="mydomain.de",
            ): DmarcMetrics(
                total_count=42,
                disposition_counts={
                    Disposition.QUARANTINE: 3,
                    Disposition.NONE_VALUE: 39,
                },
                dmarc_compliant_count=39,
                dkim_aligned_count=39,
                dkim_pass_count=39,
                spf_pass_count=42,
                spf_aligned_count=42,
            ),
            Meta(
                reporter="yahoo.com",
                from_domain="mydomain.de",
                dkim_domain="sub.mydomain.de",
                spf_domain="mydomain.de",
            ): DmarcMetrics(
                total_count=1,
                disposition_counts={Disposition.NONE_VALUE: 1},
                dmarc_compliant_count=1,
                dkim_aligned_count=1,
                dkim_pass_count=1,
                spf_pass_count=1,
                spf_aligned_count=1,
            ),
        },
        invalid_reports={InvalidMeta("someone@example.org"): 42},
    )

    exporter = PrometheusExporter(metrics)
    async with exporter.start_server() as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{server.host}:{server.port}/metrics"
            ) as response:
                served_metrics = text_string_to_metric_families(await response.text())

    samples = [
        sample for served_metric in served_metrics for sample in served_metric.samples
    ]
    expected_metrics = {
        "dmarc_total": lambda m: m.total_count,
        "dmarc_compliant_total": lambda m: m.dmarc_compliant_count,
        "dmarc_quarantine_total": lambda m: m.disposition_counts.get(
            Disposition.QUARANTINE, 0
        ),
        "dmarc_reject_total": lambda m: m.disposition_counts.get(Disposition.REJECT, 0),
        "dmarc_dkim_aligned_total": lambda m: m.dkim_aligned_count,
        "dmarc_dkim_pass_total": lambda m: m.dkim_pass_count,
        "dmarc_spf_aligned_total": lambda m: m.spf_aligned_count,
        "dmarc_spf_pass_total": lambda m: m.spf_pass_count,
    }
    for meta, metric in metrics.items():
        for prometheus_name, getter in expected_metrics.items():
            assert (
                Sample(
                    prometheus_name,
                    labels=dataclasses.asdict(meta),
                    value=getter(metric),
                    timestamp=None,
                    exemplar=None,
                )
                in samples
            )
    assert Sample(
        "dmarc_invalid_reports_total",
        labels={"from_email": "someone@example.org"},
        value=42,
        timestamp=None,
        exemplar=None,
    )


@pytest.mark.asyncio
async def test_build_info():
    exporter = PrometheusExporter(DmarcMetricsCollection())
    async with exporter.start_server() as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{server.host}:{server.port}/metrics"
            ) as response:
                served_metrics = text_string_to_metric_families(await response.text())

    samples = [
        sample for served_metric in served_metrics for sample in served_metric.samples
    ]
    assert (
        Sample(
            "dmarc_metrics_exporter_build_info",
            labels={"version": dmarc_metrics_exporter.__version__},
            value=1,
            timestamp=None,
            exemplar=None,
        )
        in samples
    )
