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

    def _capture_request(self, driver):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["timeout"] = timeout
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse('{"status":"ok"}')

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            driver.rf_on()

        return captured

    def _capture_requests(self, driver):
        captured = []

        def fake_urlopen(req, timeout):
            payload = None
            if req.data is not None:
                payload = json.loads(req.data.decode("utf-8"))
            captured.append(
                {
                    "url": req.full_url,
                    "method": req.get_method(),
                    "timeout": timeout,
                    "payload": payload,
                }
            )
            return _FakeResponse('{"status":"ok"}')

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            driver.rf_on()

        return captured

    def test_device_type_defaults_to_rxcc(self):
        driver = self.make_driver()
        self.assertEqual(driver.device_type, "rxcc")

    def test_set_device_type_normalizes_case(self):
        driver = self.make_driver()
        driver.set_device_type("Hendrix_Tx")
        self.assertEqual(driver.device_type, "hendrix_tx")

    def test_unknown_device_type_is_rejected(self):
        driver = self.make_driver()
        with self.assertRaisesRegex(ValueError, "device_type"):
            driver.set_device_type("unknown")

    def test_invalid_ctx_value_is_rejected(self):
        driver = self.make_driver()
        with self.assertRaisesRegex(ValueError, "CTX"):
            driver.set_ctx(2)

    def test_rxcc_start_uses_unified_per_device_path_and_payload(self):
        driver = self.make_driver()
        driver.set_device_type("rxcc")
        driver.set_channel(17)
        driver.set_power_level(6)
        driver.set_antenna("secondary")

        captured = self._capture_request(driver)

        self.assertEqual(
            captured["url"],
            "http://example.test:8000/api/devices/rxcc/commands/start-rf",
        )
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["timeout"], driver.timeout)
        self.assertEqual(
            captured["payload"],
            {"antenna": "secondary", "channel": 17, "power": 6},
        )
        self.assertTrue(driver.rf_enabled)

    def test_wireless_pro_rx_start_uses_wirepro_payload(self):
        driver = self.make_driver()
        driver.set_device_type("wireless-pro-rx")
        driver.set_antenna("main")
        driver.set_channel(17)
        driver.set_power_level(6)
        driver.set_wirepro_freq(78)
        driver.set_wirepro_power(-4)

        captured = self._capture_request(driver)

        self.assertEqual(
            captured["url"],
            "http://example.test:8000/api/devices/wireless-pro-rx/commands/start-rf",
        )
        self.assertEqual(
            captured["payload"],
            {
                "device": "wireless-pro-rx",
                "antenna": "main",
                "wirepro_freq": 78,
                "wirepro_power": -4.0,
            },
        )

    def test_hendrix_tx_start_posts_ctx_high_before_rf_start_by_default(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_tx")
        driver.set_channel(17)
        driver.set_power_level(6)

        captured = self._capture_requests(driver)

        self.assertEqual(
            captured,
            [
                {
                    "url": "http://example.test:8000/api/ctx/tx/high",
                    "method": "POST",
                    "timeout": driver.timeout,
                    "payload": None,
                },
                {
                    "url": "http://example.test:8000/api/devices/tx/commands/start-rf",
                    "method": "POST",
                    "timeout": driver.timeout,
                    "payload": {"channel": 17, "power": 6},
                },
            ],
        )

    def test_hendrix_tx_start_can_post_ctx_low_before_rf_start(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_tx")
        driver.set_ctx(0)
        driver.set_channel(17)
        driver.set_power_level(6)

        captured = self._capture_requests(driver)

        self.assertEqual(captured[0]["url"], "http://example.test:8000/api/ctx/tx/low")
        self.assertEqual(captured[0]["payload"], None)
        self.assertEqual(
            captured[1]["url"],
            "http://example.test:8000/api/devices/tx/commands/start-rf",
        )
        self.assertEqual(captured[1]["payload"], {"channel": 17, "power": 6})

    def test_hendrix_rx_start_posts_ctx_high_before_rf_start_by_default(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_rx")
        driver.set_channel(17)
        driver.set_power_level(6)

        captured = self._capture_requests(driver)

        self.assertEqual(
            captured,
            [
                {
                    "url": "http://example.test:8000/api/ctx/rx/high",
                    "method": "POST",
                    "timeout": driver.timeout,
                    "payload": None,
                },
                {
                    "url": "http://example.test:8000/api/devices/rx/commands/start-rf",
                    "method": "POST",
                    "timeout": driver.timeout,
                    "payload": {"channel": 17, "power": 6},
                },
            ],
        )

    def test_rxcc_stop_uses_unified_per_device_path(self):
        driver = self.make_driver()
        driver.set_device_type("rxcc")

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
            "http://example.test:8000/api/devices/rxcc/commands/stop-rf",
        )
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["payload"], {})
        self.assertFalse(driver.rf_enabled)

    def test_hendrix_tx_stop_uses_unified_per_device_path(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_tx")

        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse('{"status":"ok"}')

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            driver.rf_off()

        self.assertEqual(
            captured["url"],
            "http://example.test:8000/api/devices/tx/commands/stop-rf",
        )
        self.assertEqual(captured["payload"], {})

    def test_hendrix_rx_stop_uses_unified_per_device_path(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_rx")

        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse('{"status":"ok"}')

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            driver.rf_off()

        self.assertEqual(
            captured["url"],
            "http://example.test:8000/api/devices/rx/commands/stop-rf",
        )
        self.assertEqual(captured["payload"], {})

    def test_hendrix_tx_battery_info_calls_http_endpoint(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_tx")
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["timeout"] = timeout
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse(
                '{"operation":"read_battery","status":"ok","device":"tx","battery_mv":3812,"reports_sent":1}'
            )

        with patch("equipment.signal_generator.rxcc.request.urlopen", side_effect=fake_urlopen):
            battery_info = driver.read_battery_info()

        self.assertEqual(battery_info, {"battery_mv": 3812})
        self.assertEqual(captured["url"], "http://example.test:8000/api/battery/tx")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["timeout"], driver.timeout)
        self.assertEqual(captured["payload"], {})

    def test_hendrix_tx_battery_info_rejects_missing_battery_mv(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_tx")

        with patch(
            "equipment.signal_generator.rxcc.request.urlopen",
            side_effect=lambda req, timeout: _FakeResponse(
                '{"operation":"read_battery","status":"ok","device":"tx","reports_sent":1}'
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "missing battery_mv"):
                driver.read_battery_info()

    def test_missing_channel_fails_for_all_device_types(self):
        for device_type in ("rxcc", "hendrix_tx", "hendrix_rx"):
            driver = self.make_driver()
            driver.set_device_type(device_type)
            driver.set_power_level(4)
            if device_type == "rxcc":
                driver.set_antenna("main")

            with self.assertRaisesRegex(RuntimeError, "channel"):
                driver.rf_on()

    def test_missing_power_level_fails_for_all_device_types(self):
        for device_type in ("rxcc", "hendrix_tx", "hendrix_rx"):
            driver = self.make_driver()
            driver.set_device_type(device_type)
            driver.set_channel(11)
            if device_type == "rxcc":
                driver.set_antenna("main")

            with self.assertRaisesRegex(RuntimeError, "power_level"):
                driver.rf_on()

    def test_missing_antenna_fails_only_for_rxcc(self):
        driver = self.make_driver()
        driver.set_device_type("rxcc")
        driver.set_channel(11)
        driver.set_power_level(4)

        with self.assertRaisesRegex(RuntimeError, "antenna"):
            driver.rf_on()

    def test_wireless_pro_rx_requires_wirepro_fields_and_antenna(self):
        driver = self.make_driver()
        driver.set_device_type("wireless-pro-rx")
        driver.set_channel(11)
        driver.set_power_level(4)

        with self.assertRaisesRegex(RuntimeError, "wirepro_freq"):
            driver.rf_on()

    def test_422_maps_to_validation_error(self):
        driver = self.make_driver()
        driver.set_device_type("hendrix_tx")
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
        driver.set_device_type("hendrix_rx")
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
        driver.set_device_type("rxcc")
        driver.set_channel(1)
        driver.set_power_level(2)
        driver.set_antenna("main")

        with patch(
            "equipment.signal_generator.rxcc.request.urlopen",
            side_effect=lambda req, timeout: (_ for _ in ()).throw(
                _http_error(req.full_url, 502, '{"detail":"device communication failure"}')
            ),
        ) as mocked:
            with self.assertRaisesRegex(RuntimeError, "502"):
                driver.rf_on()

        self.assertEqual(mocked.call_count, 2)


if __name__ == "__main__":
    unittest.main()
