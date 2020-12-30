import asyncio
from unittest.mock import MagicMock

import pytest

from dmarc_metrics_exporter.app import App
from dmarc_metrics_exporter.dmarc_metrics import DmarcMetricsCollection

from .conftest import try_until_success


class ServerMock:
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, traceback):
        pass


async def async_noop():
    pass


@pytest.mark.asyncio
async def test_loads_persisted_metrics_and_stores_them_on_shutdown():
    metrics = DmarcMetricsCollection()
    metrics_provider = MagicMock()
    metrics_provider.__enter__.return_value = metrics
    exporter = MagicMock()
    exporter.start_server.return_value = ServerMock()
    exporter.get_metrics.return_value = metrics_provider
    exporter_cls = MagicMock()
    exporter_cls.return_value = exporter
    metrics_persister = MagicMock()
    metrics_persister.load.return_value = metrics
    imap_queue = MagicMock()
    imap_queue.stop_consumer.return_value = async_noop()
    app = App(
        prometheus_addr=("127.0.0.1", 9119),
        imap_queue=imap_queue,
        exporter_cls=exporter_cls,
        metrics_persister=metrics_persister,
        autosave_interval_seconds=None,
    )
    main = asyncio.create_task(app.run())

    try:
        await try_until_success(
            metrics_persister.load.assert_called_once, timeout_seconds=2
        )
    finally:
        main.cancel()
        await main
    metrics_persister.save.assert_called_once_with(metrics)


@pytest.mark.asyncio
async def test_metrics_autosave():
    metrics = DmarcMetricsCollection()
    metrics_provider = MagicMock()
    metrics_provider.__enter__.return_value = metrics
    exporter = MagicMock()
    exporter.start_server.return_value = ServerMock()
    exporter.get_metrics.return_value = metrics_provider
    exporter_cls = MagicMock()
    exporter_cls.return_value = exporter
    metrics_persister = MagicMock()
    metrics_persister.load.return_value = metrics
    imap_queue = MagicMock()
    imap_queue.stop_consumer.return_value = async_noop()
    app = App(
        prometheus_addr=("127.0.0.1", 9119),
        imap_queue=imap_queue,
        exporter_cls=exporter_cls,
        metrics_persister=metrics_persister,
        autosave_interval_seconds=0.5,
    )
    main = asyncio.create_task(app.run())

    try:
        await asyncio.sleep(1)
        metrics_persister.save.assert_called_with(metrics)
    finally:
        main.cancel()
        await main
