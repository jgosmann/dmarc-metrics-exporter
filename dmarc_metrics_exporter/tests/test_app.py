import asyncio
from dataclasses import dataclass, field, fields
from typing import Tuple
from unittest.mock import MagicMock

import pytest

from dmarc_metrics_exporter.app import App
from dmarc_metrics_exporter.dmarc_metrics import DmarcMetricsCollection, InvalidMeta
from dmarc_metrics_exporter.tests.sample_emails import (
    create_email_with_attachment,
    create_minimal_email,
    create_zip_report,
)

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
    prometheus_addr: Tuple[str, int] = ("127.0.0.1", 9797)
    exporter_cls: MagicMock = field(default_factory=MagicMock)
    metrics_persister: MagicMock = field(default_factory=MagicMock)
    imap_queue: MagicMock = field(default_factory=MagicMock)

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


@pytest.mark.asyncio
async def test_processes_duplicate_report_only_once():
    mocks = AppMocks()
    app = App(autosave_interval_seconds=0.5, **mocks.dependencies.as_flat_dict())
    email = create_email_with_attachment(create_zip_report())

    await app.process_email(email)
    await app.process_email(email)

    assert sum(m.total_count for m in mocks.metrics.values()) == 1


@pytest.mark.asyncio
async def test_counts_failed_extractions():
    mocks = AppMocks()
    app = App(autosave_interval_seconds=0.5, **mocks.dependencies.as_flat_dict())
    email = create_minimal_email()

    await app.process_email(email)

    assert mocks.metrics.invalid_reports == {InvalidMeta(email["From"]): 1}
