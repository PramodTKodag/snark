"""Minimal JSON log formatter — stdlib only, no dependency.

Serializes each log record plus any ``extra=`` fields to a single JSON line so
aggregators (Loki/LogQL) can filter by field. Selected via LOG_FORMAT=json.
"""

import json
import logging

# Standard LogRecord attributes we don't want to duplicate into the payload;
# anything else on the record came from an ``extra=`` dict.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
