import argparse
import asyncio
import json
from email.message import EmailMessage
from typing import Sequence, Tuple

from dmarc_metrics_exporter.deserialization import (
    convert_to_events,
    get_aggregate_report_from_email,
)
from dmarc_metrics_exporter.dmarc_metrics import DmarcMetricsCollection
from dmarc_metrics_exporter.imap_queue import ConnectionConfig, ImapQueue, QueueFolders
from dmarc_metrics_exporter.prometheus_exporter import PrometheusExporter


def main(argv: Sequence[str]):
    parser = argparse.ArgumentParser(
        description="Monitor an IMAP account for DMARC aggregate reports and "
        "provide a Prometheus endpoint for metrics derived from incoming "
        "reports."
    )
    parser.add_argument(
        "--configuration",
        nargs=1,
        type=argparse.FileType("r"),
        default="/etc/dmarc-metrics-exporter.json",
        help="Configuration file",
    )
    args = parser.parse_args(argv)

    configuration = json.load(args.configuration[0])
    args.configuration[0].close()
    app = App(
        prometheus_addr=(
            configuration.get("listen_addr", "127.0.0.1"),
            configuration.get("port", 9119),
        ),
        imap_connection=ConnectionConfig(**configuration["imap"]),
        folders=QueueFolders(**configuration.get("folders", {})),
        poll_interval_seconds=configuration.get("poll_interval_seconds", 60),
    )

    asyncio.run(app.run())


class App:
    def __init__(
        self,
        prometheus_addr: Tuple[str, int],
        imap_connection: ConnectionConfig,
        folders: QueueFolders,
        poll_interval_seconds: int,
    ):
        self.prometheus_addr = prometheus_addr
        self.exporter = PrometheusExporter(DmarcMetricsCollection())
        self.imap_queue = ImapQueue(
            connection=imap_connection,
            folders=folders,
            poll_interval_seconds=poll_interval_seconds,
        )

    async def run(self):
        try:
            self.imap_queue.consume(self.process_email)
            async with self.exporter.start_server(*self.prometheus_addr):
                while True:
                    await asyncio.sleep(1)
        finally:
            self.imap_queue.stop_consumer()

    async def process_email(self, msg: EmailMessage):
        for report in get_aggregate_report_from_email(msg):
            for event in convert_to_events(report):
                with self.exporter.get_metrics() as metrics:
                    metrics.update(event)
