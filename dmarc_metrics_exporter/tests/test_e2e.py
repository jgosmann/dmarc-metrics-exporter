import json
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import asdict

import aiohttp
import pytest
from prometheus_client.parser import text_string_to_metric_families
from prometheus_client.samples import Sample

from .conftest import send_email, try_until_success, verify_imap_available
from .sample_emails import create_email_with_zip_attachment


@contextmanager
def dmarc_metrics_exporter(config_path):
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "dmarc_metrics_exporter",
            "--configuration",
            str(config_path),
        ],
        stdout=sys.stdout,
        stderr=sys.stderr,
        encoding="utf-8",
    )
    yield proc
    proc.terminate()
    try:
        proc.wait(20)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.asyncio
async def test_successful_processing_of_existing_queue_message(greenmail, tmp_path):
    # Given
    msg = create_email_with_zip_attachment(greenmail.imap.username)
    await try_until_success(lambda: send_email(msg, greenmail.smtp))
    await try_until_success(lambda: verify_imap_available(greenmail.imap))

    config = {
        "listen_addr": "127.0.0.1",
        "port": 9119,
        "imap": asdict(greenmail.imap),
        "poll_interval_seconds": 1,
        "metrics_db": str(tmp_path / "metrics.db"),
    }
    config_path = tmp_path / "dmarc-metrics-exporter.conf"
    with open(config_path, "w") as f:
        json.dump(config, f)

    # When
    expected_meta = {
        "reporter": "google.com",
        "from_domain": "mydomain.de",
        "dkim_domain": "mydomain.de",
        "spf_domain": "my-spf-domain.de",
    }
    expected_metrics = {
        "dmarc_total": 1,
        "dmarc_compliant_total": 1,
        "dmarc_quarantine_total": 0,
        "dmarc_reject_total": 0,
        "dmarc_dkim_aligned_total": 1,
        "dmarc_dkim_pass_total": 1,
        "dmarc_spf_aligned_total": 0,
        "dmarc_spf_pass_total": 1,
    }

    with dmarc_metrics_exporter(config_path):
        await try_until_success(
            lambda: assert_exported_metrics(
                f"http://{config['listen_addr']}:{config['port']}/metrics",
                expected_meta,
                expected_metrics,
            ),
            timeout_seconds=20,
        )


async def assert_exported_metrics(url, expected_meta, expected_metrics):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            served_metrics = text_string_to_metric_families(await response.text())

    samples = [
        sample for served_metric in served_metrics for sample in served_metric.samples
    ]
    for prometheus_name, value in expected_metrics.items():
        assert (
            Sample(
                prometheus_name,
                labels=expected_meta,
                value=value,
                timestamp=None,
                exemplar=None,
            )
            in samples
        )
