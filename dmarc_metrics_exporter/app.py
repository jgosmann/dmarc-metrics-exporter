import argparse
import asyncio
import json
from asyncio import CancelledError
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Tuple

import structlog

from dmarc_metrics_exporter.deserialization import (
    ReportExtractionError,
    convert_to_events,
    get_aggregate_report_from_email,
)
from dmarc_metrics_exporter.dmarc_metrics import DmarcMetricsCollection, InvalidMeta
from dmarc_metrics_exporter.expiring_set import ExpiringSet
from dmarc_metrics_exporter.imap_queue import ConnectionConfig, ImapQueue, QueueFolders
from dmarc_metrics_exporter.logging import configure_logging
from dmarc_metrics_exporter.metrics_persister import MetricsPersister
from dmarc_metrics_exporter.prometheus_exporter import PrometheusExporter

logger = structlog.get_logger()


def main(argv: Sequence[str]):
    parser = argparse.ArgumentParser(
        description="Monitor an IMAP account for DMARC aggregate reports and "
        "provide a Prometheus endpoint for metrics derived from incoming "
        "reports."
    )
    parser.add_argument(
        "--configuration",
        type=argparse.FileType("r"),
        default="/etc/dmarc-metrics-exporter.json",
        help="Configuration file",
    )
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    configuration = json.load(args.configuration)
    args.configuration.close()

    configure_logging(configuration.get("logging", {}), debug=args.debug)

    storage_path = Path(
        configuration.get("storage_path", "/var/lib/dmarc-metrics-exporter")
    )
    app = App(
        prometheus_addr=(
            configuration.get("listen_addr", "127.0.0.1"),
            configuration.get("port", 9797),
        ),
        imap_queue=ImapQueue(
            connection=ConnectionConfig(**configuration["imap"]),
            folders=QueueFolders(**configuration.get("folders", {})),
            poll_interval_seconds=configuration.get("poll_interval_seconds", 60),
        ),
        metrics_persister=MetricsPersister(storage_path / "metrics.db"),
        deduplication_max_seconds=configuration.get(
            "deduplication_max_seconds", 7 * 24 * 60 * 60
        ),
        seen_reports_db=storage_path / "seen-reports.db",
    )

    asyncio.run(app.run())


class App:
    # pylint: disable=too-many-instance-attributes
    _seen_reports: ExpiringSet[Tuple[str, str]]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        *,
        prometheus_addr: Tuple[str, int],
        imap_queue: ImapQueue,
        metrics_persister: MetricsPersister,
        exporter_cls: Callable[[DmarcMetricsCollection], Any] = PrometheusExporter,
        autosave_interval_seconds: float = 60,
        deduplication_max_seconds: float = 7 * 24 * 60 * 60,
        seen_reports_db: Optional[Path] = None
    ):
        self.prometheus_addr = prometheus_addr
        self.exporter = exporter_cls(DmarcMetricsCollection())
        self.imap_queue = imap_queue
        self.exporter_cls = exporter_cls
        self.metrics_persister = metrics_persister
        self.autosave_interval_seconds = autosave_interval_seconds
        self.seen_reports_db = seen_reports_db
        if seen_reports_db and seen_reports_db.exists():
            self._seen_reports = ExpiringSet.load(
                seen_reports_db, deduplication_max_seconds
            )
        else:
            self._seen_reports = ExpiringSet(deduplication_max_seconds)

    async def run(self):
        self.exporter = self.exporter_cls(self.metrics_persister.load())
        try:
            self.imap_queue.consume(self.process_email)
            async with self.exporter.start_server(*self.prometheus_addr):
                while True:
                    await asyncio.sleep(self.autosave_interval_seconds or 60)
                    if self.autosave_interval_seconds:
                        self._save_metrics()
        except CancelledError:
            pass
        finally:
            self._save_metrics()
            await self.imap_queue.stop_consumer()

    def _save_metrics(self):
        with self.exporter.get_metrics() as metrics:
            self.metrics_persister.save(metrics)
        if self.seen_reports_db:
            self._seen_reports.persist(self.seen_reports_db)

    async def process_email(self, msg: EmailMessage):
        try:
            for report in get_aggregate_report_from_email(msg):
                org_name = report.report_metadata and report.report_metadata.org_name
                report_id = report.report_metadata and report.report_metadata.report_id
                if org_name and report_id:
                    if (org_name, report_id) in self._seen_reports:
                        continue
                    self._seen_reports.add((org_name, report_id))

                for event in convert_to_events(report):
                    with self.exporter.get_metrics() as metrics:
                        metrics.update(event)
        except ReportExtractionError as err:
            with self.exporter.get_metrics() as metrics:
                metrics.inc_invalid(InvalidMeta(err.msg.get("from", None)))
            logger.warning(str(err), exc_info=err, msg=err.msg)
