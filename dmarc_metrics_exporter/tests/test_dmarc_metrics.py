from dmarc_metrics_exporter.dmarc_event import (
    Disposition,
    DmarcEvent,
    DmarcResult,
    Meta,
)
from dmarc_metrics_exporter.dmarc_metrics import DmarcMetrics, DmarcMetricsCollection


def test_dmarc_metrics_upate():
    metrics = DmarcMetrics()
    metrics.update(
        2,
        DmarcResult(
            disposition=Disposition.QUARANTINE,
            dkim_pass=True,
            dkim_aligned=False,
            spf_pass=True,
            spf_aligned=True,
        ),
    )
    assert metrics == DmarcMetrics(
        total_count=2,
        disposition_counts={
            Disposition.QUARANTINE: 2,
        },
        dmarc_compliant_count=2,
        dkim_pass_count=2,
        spf_aligned_count=2,
        spf_pass_count=2,
    )


def test_dmarc_metrics_collection_update():
    metrics_collector = DmarcMetricsCollection({})
    meta = Meta(
        reporter="google.com",
        from_domain="mydomain.de",
        dkim_domain="sub.mydomain.de",
        spf_domain="mydomain.de",
    )
    result = DmarcResult(
        disposition=Disposition.NONE_VALUE,
        dkim_pass=False,
        dkim_aligned=False,
        spf_pass=False,
        spf_aligned=False,
    )
    metrics_collector.update(DmarcEvent(count=1, meta=meta, result=result))
    assert metrics_collector.metrics == {
        meta: DmarcMetrics(
            total_count=1, disposition_counts={Disposition.NONE_VALUE: 1}
        )
    }
