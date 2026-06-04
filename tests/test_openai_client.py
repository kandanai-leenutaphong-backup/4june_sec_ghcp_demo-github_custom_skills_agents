import io
import json
import logging
import unittest

from openai_client import call_azure_openai_with_retry
from openai_logging import LOGGER_NAME


class FakeAzureError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


class RetryLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stream = io.StringIO()
        self.logger = logging.getLogger(LOGGER_NAME)
        self.logger.handlers = []
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(logging.StreamHandler(self.stream))

    def test_retries_on_429_then_returns_success(self) -> None:
        calls = {"count": 0}

        def request_fn() -> FakeResponse:
            calls["count"] += 1
            if calls["count"] == 1:
                raise FakeAzureError("rate limited", 429)
            return FakeResponse(200)

        sleeps: list[float] = []
        times = iter([10.0, 10.01, 10.1, 10.11])
        response = call_azure_openai_with_retry(
            request_fn,
            correlation_id="corr-123",
            max_retries=2,
            base_backoff_seconds=0.5,
            max_backoff_seconds=2.0,
            sleep_fn=sleeps.append,
            time_fn=lambda: next(times),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls["count"], 2)
        self.assertEqual(sleeps, [0.5])

        logs = [json.loads(line) for line in self.stream.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0]["correlation_id"], "corr-123")
        self.assertFalse(logs[0]["success"])
        self.assertTrue(logs[0]["retryable"])
        self.assertEqual(logs[1]["correlation_id"], "corr-123")
        self.assertTrue(logs[1]["success"])
        self.assertIn("latency_ms", logs[1])

    def test_retries_on_5xx_until_max_retries_then_raises(self) -> None:
        calls = {"count": 0}

        def request_fn() -> FakeResponse:
            calls["count"] += 1
            raise FakeAzureError("server error", 503)

        sleeps: list[float] = []
        times = iter([1.0, 1.01, 2.0, 2.02, 3.0, 3.03])
        with self.assertRaises(FakeAzureError):
            call_azure_openai_with_retry(
                request_fn,
                correlation_id="corr-500",
                max_retries=2,
                base_backoff_seconds=0.2,
                max_backoff_seconds=1.0,
                sleep_fn=sleeps.append,
                time_fn=lambda: next(times),
            )

        self.assertEqual(calls["count"], 3)
        self.assertEqual(sleeps, [0.2, 0.4])

        logs = [json.loads(line) for line in self.stream.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(logs), 3)
        self.assertTrue(all(not entry["success"] for entry in logs))
        self.assertTrue(all(entry["retryable"] for entry in logs))


if __name__ == "__main__":
    unittest.main()
