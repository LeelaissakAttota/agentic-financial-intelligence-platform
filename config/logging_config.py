"""Structured JSON logging setup. TODO (Day 1)."""

import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    )
