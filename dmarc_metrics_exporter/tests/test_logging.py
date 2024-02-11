import json
import logging
import re

import pytest
import structlog

from dmarc_metrics_exporter.logging import configure_logging, parse_log_level


@pytest.fixture(autouse=True)
def reset_logging_config_after_test():
    yield None
    logging.Logger.manager.loggerDict.clear()
    configure_logging({}, debug=True)


def test_parse_log_level_returns_int_for_int_arg():
    assert parse_log_level(20) == 20
    assert parse_log_level(40) == 40


@pytest.mark.parametrize(
    "input_level,output",
    [
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("warning", logging.WARNING),
        ("error", logging.ERROR),
        ("critical", logging.CRITICAL),
    ],
)
def test_parse_log_level_parses_string_levels(input_level, output):
    assert parse_log_level(input_level) == output


@pytest.mark.parametrize(
    "input_level,output",
    [
        ("info", logging.INFO),
        ("INFO", logging.INFO),
        ("iNfO", logging.INFO),
        ("ERRor", logging.ERROR),
    ],
)
def test_parse_log_level_is_case_insensitive(input_level, output):
    assert parse_log_level(input_level) == output


def test_configure_logging_setting_log_level(caplog):
    configure_logging(
        {
            "root": {"level": "WARNING"},
        },
        debug=False,
    )
    structlog_logger = structlog.get_logger("test-logger")
    stdlib_logger = logging.getLogger("test-logger")
    logging.getLogger().addHandler(caplog.handler)

    for logger in (structlog_logger, stdlib_logger):
        logger.debug("not_visible")
        logger.warning("visible")

    assert caplog.record_tuples == [
        ("test-logger", logging.WARNING, "{'event': 'visible', 'level': 'warning'}"),
        ("test-logger", logging.WARNING, "visible"),
    ]


def test_configure_logging_debug_overrides_log_level(caplog):
    configure_logging(
        {
            "root": {"level": "WARNING"},
        },
        debug=True,
    )
    structlog_logger = structlog.get_logger("test-logger")
    stdlib_logger = logging.getLogger("test-logger")
    logging.getLogger().addHandler(caplog.handler)

    for logger in (structlog_logger, stdlib_logger):
        logger.debug("visible")

    assert caplog.record_tuples == [
        ("test-logger", logging.DEBUG, "{'event': 'visible', 'level': 'debug'}"),
        ("test-logger", logging.DEBUG, "visible"),
    ]


def test_configure_logging_default_log_message_format(caplog, capsys):
    configure_logging(
        {},
        debug=False,
    )
    structlog_logger = structlog.get_logger("test-logger").bind(logger="test-logger")
    stdlib_logger = logging.getLogger("test-logger")
    logging.getLogger().addHandler(caplog.handler)

    structlog_logger.warning("event", some_key="some_value")
    stdlib_logger.warning("event", extra={"some_key": "some_value"})

    captured = capsys.readouterr()
    without_color = re.sub("\x1b\\[\\d+m", "", captured.err)
    timestamp = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
    spacing = " " * 24
    assert re.match(
        f"^{timestamp} \\[warning  \\] event {spacing} \\[test-logger\\] some_key=some_value\n"
        f"{timestamp} \\[warning  \\] event {spacing} \\[test-logger\\] some_key=some_value\n$",
        without_color,
    )


def test_configure_logging_to_log_json(caplog, capsys):
    configure_logging(
        {
            "handlers": {
                "default": {"class": "logging.StreamHandler", "formatter": "json"}
            },
        },
        debug=False,
    )
    structlog_logger = structlog.get_logger("test-logger").bind(logger="test-logger")
    stdlib_logger = logging.getLogger("test-logger")
    logging.getLogger().addHandler(caplog.handler)

    structlog_logger.warning("event", some_key="some_value")
    stdlib_logger.warning("event", extra={"some_key": "some_value"})

    captured = capsys.readouterr()
    for line in captured.err.splitlines():
        doc = json.loads(line)
        del doc["timestamp"]
        assert doc == {
            "level": "warning",
            "logger": "test-logger",
            "event": "event",
            "some_key": "some_value",
        }


def test_configure_logging_disable_stdlib_sublogger(caplog):
    configure_logging(
        {
            "loggers": {"sublogger": {"propagate": False}},
        },
        debug=False,
    )
    stdlib_logger = logging.getLogger("sublogger")
    logging.getLogger().addHandler(caplog.handler)

    stdlib_logger.warning("not_visible")

    assert caplog.record_tuples == []
