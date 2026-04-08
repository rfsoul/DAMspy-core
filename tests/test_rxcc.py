import io
import json
import os
import sys
import unittest
from urllib import error
from unittest.mock import patch


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from equipment.signal_generator.rxcc import RXCC


class _FakeResponse:
    def __init__(self, body="{}"):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _http_error(url: str, code: int, body: str):
    return error.HTTPError(
        url=url,
        code=code,
        msg=f"HTTP {code}",
        hdrs=None,
        fp=io.BytesIO(body.encode("utf-8")),
    )


class RXCCTests(unittest.TestCase):
    def make_driver(self, *, max_retries=0):
        driver = RXCC(
            {
                "rpicontrol_ipaddress": "http://example.test:8000",
                "max_retries": max_retries,
            }
        )
        driver._is_open = True
        return driver

    def test_start_tx_rf_uses_unified_command_path_and_payload(self):
        driver = self.make_driver()
        driver.set_channel(17)
        driver.set_power_level(6)

        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["timeout"] = timeout
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse('{"status":"ok"}')

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            driver.rf_on()

        self.assertEqual(
            captured["url"],
            "http://example.test:8000/api/devices/tx/commands/start-rf",
        )
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["timeout"], driver.timeout)
        self.assertEqual(captured["payload"], {"channel": 17, "power": 6})
        self.assertTrue(driver.rf_enabled)

    def test_stop_tx_rf_uses_unified_command_path(self):
        driver = self.make_driver()

        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse('{"status":"ok"}')

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            driver.rf_off()

        self.assertEqual(
            captured["url"],
            "http://example.test:8000/api/devices/tx/commands/stop-rf",
        )
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["payload"], {})
        self.assertFalse(driver.rf_enabled)

    def test_start_tx_rf_requires_channel(self):
        driver = self.make_driver()
        driver.set_power_level(4)

        with self.assertRaisesRegex(RuntimeError, "channel"):
            driver.rf_on()

    def test_start_tx_rf_requires_power_level(self):
        driver = self.make_driver()
        driver.set_channel(11)

        with self.assertRaisesRegex(RuntimeError, "power_level"):
            driver.rf_on()

    def test_422_maps_to_validation_error(self):
        driver = self.make_driver()
        driver.set_channel(1)
        driver.set_power_level(2)

        with patch(
            "equipment.signal_generator.rxcc.request.urlopen",
            side_effect=lambda req, timeout: (_ for _ in ()).throw(
                _http_error(req.full_url, 422, '{"detail":"unsupported command"}')
            ),
        ) as mocked:
            with self.assertRaisesRegex(ValueError, "422"):
                driver.rf_on()

        self.assertEqual(mocked.call_count, 1)

    def test_503_maps_to_device_unavailable(self):
        driver = self.make_driver()
        driver.set_channel(1)
        driver.set_power_level(2)

        with patch(
            "equipment.signal_generator.rxcc.request.urlopen",
            side_effect=lambda req, timeout: (_ for _ in ()).throw(
                _http_error(req.full_url, 503, '{"detail":"device unavailable"}')
            ),
        ) as mocked:
            with self.assertRaisesRegex(RuntimeError, "503"):
                driver.rf_on()

        self.assertEqual(mocked.call_count, 1)

    def test_502_maps_to_communication_failure_after_retries(self):
        driver = self.make_driver(max_retries=1)
        driver.set_channel(1)
        driver.set_power_level(2)

        with patch(
            "equipment.signal_generator.rxcc.request.urlopen",
            side_effect=lambda req, timeout: (_ for _ in ()).throw(
                _http_error(req.full_url, 502, '{"detail":"device communication failure"}')
            ),
        ) as mocked:
            with self.assertRaisesRegex(RuntimeError, "502"):
                driver.rf_on()

        self.assertEqual(mocked.call_count, 2)

    def test_start_rxcc_rf_keeps_legacy_path_available(self):
        driver = self.make_driver()

        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse('{"status":"ok"}')

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            driver.start_rxcc_rf(antenna="main", channel=3, power=7)

        self.assertEqual(captured["url"], "http://example.test:8000/api/rf/start")
        self.assertEqual(
            captured["payload"],
            {"antenna": "main", "channel": 3, "power": 7},
        )


if __name__ == "__main__":
    unittest.main()
