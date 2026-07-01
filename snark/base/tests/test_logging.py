import json
import logging
import sys

from base.logging import JsonFormatter


class TestJsonFormatter:
    def test_serializes_core_fields_and_extras(self):
        record = logging.makeLogRecord(
            {
                "name": "wit.services",
                "levelname": "INFO",
                "levelno": logging.INFO,
                "msg": "generation",
                "event": "generation",
                "cost_usd": 0.01,
                "streamed": False,
            }
        )

        payload = json.loads(JsonFormatter().format(record))

        assert payload["level"] == "INFO"
        assert payload["logger"] == "wit.services"
        assert payload["msg"] == "generation"
        assert payload["event"] == "generation"
        assert payload["cost_usd"] == 0.01
        assert payload["streamed"] is False
        assert "ts" in payload

    def test_output_is_a_single_json_line(self):
        record = logging.makeLogRecord({"msg": "hello", "levelname": "INFO"})
        line = JsonFormatter().format(record)
        assert "\n" not in line
        json.loads(line)  # valid JSON

    def test_reserved_record_attributes_are_not_duplicated(self):
        record = logging.makeLogRecord({"msg": "hi", "levelname": "INFO"})
        payload = json.loads(JsonFormatter().format(record))
        # Internal LogRecord machinery must not leak into the payload.
        assert "args" not in payload
        assert "levelno" not in payload
        assert "pathname" not in payload

    def test_non_serializable_extra_is_stringified(self):
        record = logging.makeLogRecord(
            {"msg": "x", "levelname": "INFO", "obj": object()}
        )
        # default=str keeps a stray object from raising during serialization.
        payload = json.loads(JsonFormatter().format(record))
        assert "obj" in payload

    def test_includes_exception_when_present(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.LogRecord(
                "wit", logging.ERROR, __file__, 10, "kaboom", (), sys.exc_info()
            )

        payload = json.loads(JsonFormatter().format(record))

        assert payload["level"] == "ERROR"
        assert "exc" in payload
        assert "ValueError: boom" in payload["exc"]
