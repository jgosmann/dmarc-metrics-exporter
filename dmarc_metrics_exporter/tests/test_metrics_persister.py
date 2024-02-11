from dmarc_metrics_exporter.dmarc_metrics import (
    Disposition,
    DmarcMetrics,
    DmarcMetricsCollection,
    InvalidMeta,
    Meta,
)
from dmarc_metrics_exporter.metrics_persister import MetricsPersister


def test_roundtrip_metrics(tmp_path):
    metrics_db = tmp_path / "metrics.db"
    metrics = DmarcMetricsCollection(
        {
            Meta(
                reporter="google.com",
                from_domain="mydomain.de",
                dkim_domain="dkim-domain.org",
                spf_domain="spf-domain.org",
            ): DmarcMetrics(
                total_count=42,
                disposition_counts={Disposition.QUARANTINE: 4},
                dmarc_compliant_count=24,
                dkim_aligned_count=5,
                dkim_pass_count=10,
                spf_aligned_count=4,
                spf_pass_count=8,
            )
        },
        {InvalidMeta("someone@example.com"): 42},
    )

    persister = MetricsPersister(metrics_db)
    persister.save(metrics)
    assert persister.load() == metrics


def test_loads_old_format(tmp_path):
    metrics_db = tmp_path / "metrics.db"
    metrics_db.write_text(
        "[[{"
        '"reporter":"google.com",'
        '"from_domain":"mydomain.de",'
        '"dkim_domain":"dkim-domain.org",'
        '"spf_domain":"spf-domain.org"'
        "},{"
        '"total_count":42,'
        '"disposition_counts":{"quarantine":4},'
        '"dmarc_compliant_count":24,'
        '"dkim_aligned_count":5,'
        '"dkim_pass_count":10,'
        '"spf_aligned_count":4,'
        '"spf_pass_count":8'
        "}]]"
    )

    persister = MetricsPersister(metrics_db)
    assert persister.load() == DmarcMetricsCollection(
        {
            Meta(
                reporter="google.com",
                from_domain="mydomain.de",
                dkim_domain="dkim-domain.org",
                spf_domain="spf-domain.org",
            ): DmarcMetrics(
                total_count=42,
                disposition_counts={Disposition.QUARANTINE: 4},
                dmarc_compliant_count=24,
                dkim_aligned_count=5,
                dkim_pass_count=10,
                spf_aligned_count=4,
                spf_pass_count=8,
            )
        }
    )


def test_returns_newly_initialized_metrics_if_db_is_non_existent(tmp_path):
    metrics_db = tmp_path / "metrics.db"
    persister = MetricsPersister(metrics_db)
    assert persister.load() == DmarcMetricsCollection()
