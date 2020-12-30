import asyncio
from dataclasses import dataclass, field, fields
from email.message import EmailMessage
from typing import Tuple
from unittest.mock import MagicMock

import pytest

from dmarc_metrics_exporter.app import App
from dmarc_metrics_exporter.dmarc_metrics import DmarcMetricsCollection
from dmarc_metrics_exporter.model.tests.sample_data import SAMPLE_XML

from .conftest import try_until_success


class ServerMock:
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, traceback):
        pass


async def async_noop():
    pass


@dataclass
class AppDependencies:
    prometheus_addr: Tuple[str, int] = ("127.0.0.1", 9119)
    exporter_cls: MagicMock = field(default_factory=MagicMock)
    metrics_persister: MagicMock = field(default_factory=MagicMock)
    imap_queue: MagicMock = field(default_factory=MagicMock)
    notifier: MagicMock = field(default_factory=MagicMock)

    def as_flat_dict(self):
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass
class AppMocks:
    dependencies: AppDependencies = field(default_factory=AppDependencies)
    metrics: DmarcMetricsCollection = field(default_factory=DmarcMetricsCollection)
    metrics_provider: MagicMock = field(default_factory=MagicMock)
    exporter: MagicMock = field(default_factory=MagicMock)

    def __post_init__(self):
        self.metrics_provider.__enter__.return_value = self.metrics
        self.exporter.start_server.return_value = ServerMock()
        self.exporter.get_metrics.return_value = self.metrics_provider
        self.dependencies.exporter_cls.return_value = self.exporter
        self.dependencies.metrics_persister.load.return_value = self.metrics
        self.dependencies.imap_queue.stop_consumer.side_effect = async_noop


@pytest.mark.asyncio
async def test_loads_persisted_metrics_and_stores_them_on_shutdown():
    mocks = AppMocks()
    app = App(autosave_interval_seconds=None, **mocks.dependencies.as_flat_dict())
    main = asyncio.create_task(app.run())

    try:
        await try_until_success(
            app.metrics_persister.load.assert_called_once, timeout_seconds=2
        )
    finally:
        main.cancel()
        await main
    mocks.dependencies.metrics_persister.save.assert_called_once_with(mocks.metrics)


@pytest.mark.asyncio
async def test_metrics_autosave():
    mocks = AppMocks()
    app = App(autosave_interval_seconds=0.5, **mocks.dependencies.as_flat_dict())
    main = asyncio.create_task(app.run())

    try:
        await asyncio.sleep(1)
        mocks.dependencies.metrics_persister.save.assert_called_with(mocks.metrics)
    finally:
        main.cancel()
        await main


class DummyException(Exception):
    pass


@pytest.mark.asyncio
async def test_forwards_processing_failures():
    msg = EmailMessage()
    msg.add_attachment(SAMPLE_XML, subtype="xml")

    mocks = AppMocks()
    mocks.metrics.update = MagicMock()
    mocks.metrics.update.side_effect = DummyException("raised on purpose")
    app = App(autosave_interval_seconds=None, **mocks.dependencies.as_flat_dict())
    main = asyncio.create_task(app.run())

    try:
        await asyncio.sleep(1)
        handler = mocks.dependencies.imap_queue.consume.call_args_list[0][0][0]
        try:
            await handler(msg)
        except DummyException:
            pass
        mocks.dependencies.notifier.send_message.assert_called_once()
        assert mocks.dependencies.notifier.send_message.call_args_list[0][0][0] is msg
    finally:
        main.cancel()
        await main
