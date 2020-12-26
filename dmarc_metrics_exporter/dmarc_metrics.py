from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

from dmarc_metrics_exporter.dmarc_event import (
    Disposition,
    DmarcEvent,
    DmarcResult,
    Meta,
)


@dataclass
class DmarcMetrics:
    total_count: int = 0
    disposition_counts: Dict[Disposition, int] = field(
        default_factory=lambda: defaultdict(lambda: 0)
    )
    dmarc_compliant_count: int = 0
    dkim_pass_count: int = 0
    spf_pass_count: int = 0
    dkim_aligned_count: int = 0
    spf_aligned_count: int = 0

    def update(self, count: int, result: DmarcResult):
        self.total_count += count
        self.disposition_counts[result.disposition] += count
        if result.dmarc_compliant:
            self.dmarc_compliant_count += count
        if result.dkim_pass:
            self.dkim_pass_count += count
        if result.spf_pass:
            self.spf_pass_count += count
        if result.dkim_aligned:
            self.dkim_aligned_count += count
        if result.spf_aligned:
            self.spf_aligned_count += count


@dataclass
class DmarcMetricsCollection:
    metrics: Dict[Meta, DmarcMetrics] = field(
        default_factory=lambda: defaultdict(DmarcMetrics)
    )

    def update(self, event: DmarcEvent):
        self.metrics[event.meta].update(event.count, event.result)
