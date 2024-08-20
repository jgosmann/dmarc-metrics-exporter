import logging
import logging.config
from typing import Any, Dict, Union, cast

import structlog


def configure_logging(overrides: dict, *, debug: bool):
    log_level = (
        logging.DEBUG
        if debug
        else parse_log_level(overrides.get("root", {}).get("level", logging.INFO))
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.dev.set_exc_info,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    foreign_pre_chain = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.format_exc_info,
    ]
    console_processors = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
    ]
    json_processors = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    logging_config: Dict[str, Any] = {
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "colored",
            },
        },
        "root": {},
    }
    logging_config.update(overrides)
    logging_config.update(
        {
            "version": 1,
            "incremental": False,
            "formatters": {
                "plain": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": console_processors
                    + [
                        structlog.dev.ConsoleRenderer(colors=False),
                    ],
                    "foreign_pre_chain": foreign_pre_chain,
                },
                "colored": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": console_processors
                    + [structlog.dev.ConsoleRenderer(colors=True)],
                    "foreign_pre_chain": foreign_pre_chain,
                },
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": json_processors,
                    "foreign_pre_chain": foreign_pre_chain,
                },
            },
        }
    )
    root = cast(dict, logging_config["root"])
    if "handlers" not in root:
        root.update({"handlers": ["default"]})
    root.update({"level": log_level})
    logging.config.dictConfig(logging_config)


def parse_log_level(level: Union[str, int]) -> int:
    if isinstance(level, str):
        level = level.lower()
        if level == "debug":
            return logging.DEBUG
        if level == "info":
            return logging.INFO
        if level == "warning":
            return logging.WARNING
        if level == "error":
            return logging.ERROR
        if level == "critical":
            return logging.CRITICAL
        raise ValueError("invalid log level")
    return level
