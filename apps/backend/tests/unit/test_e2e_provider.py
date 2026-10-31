import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.e2e_provider import controlled_stream, require_test_worker


class BrowserBarrierTest(unittest.TestCase):
    def test_rejects_production_and_live_providers(self):
        with TemporaryDirectory() as tmp:
            for env, provider in [("production", "fake"), ("test", "compatible_http")]:
                with self.assertRaises(RuntimeError):
                    require_test_worker(env, provider, Path(tmp))
            require_test_worker("test", "fake", Path(tmp))

    def test_first_delta_is_consumed_before_pause_and_release_is_required(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            stream = controlled_stream(iter(["first", "second"]), directory, "test")
            self.assertEqual(next(stream), "first")
            self.assertFalse((directory / "test.paused").exists())
            received = []
            thread = threading.Thread(target=lambda: received.extend(stream))
            thread.start()
            try:
                # Wait for the paused signal, not a simulated stream duration.
                for _ in range(1000):
                    if (directory / "test.paused").exists():
                        break
                    threading.Event().wait(0.001)
                self.assertTrue((directory / "test.paused").exists())
                self.assertEqual(received, [])
                (directory / "test.release").touch()
            finally:
                (directory / "test.release").touch()
                thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(received, ["second"])

    def test_missing_release_fails_closed(self):
        with TemporaryDirectory() as tmp:
            stream = controlled_stream(iter([1, 2]), Path(tmp), "test", timeout=0)
            self.assertEqual(next(stream), 1)
            with self.assertRaises(TimeoutError):
                next(stream)
            self.assertTrue((Path(tmp) / "test.timed-out").exists())
