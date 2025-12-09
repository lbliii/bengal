from types import SimpleNamespace

from bengal.server.utils import apply_dev_no_cache_headers, get_dev_config, safe_int


def test_apply_dev_no_cache_headers_adds_headers():
    collected = {}

    def sender(key, value):
        collected[key] = value

    apply_dev_no_cache_headers(SimpleNamespace(send_header=sender))
    assert "Cache-Control" in collected and "no-store" in collected["Cache-Control"]
    assert collected["Pragma"] == "no-cache"


def test_get_dev_config_nested():
    cfg = {"dev": {"watch": {"backend": "polling", "debounce_ms": 250}}}
    assert get_dev_config(cfg, "watch", "backend", default="auto") == "polling"
    assert get_dev_config(cfg, "watch", "debounce_ms", default=0) == 250
    assert get_dev_config(cfg, "watch", "missing", default=1) == 1


def test_safe_int_variants():
    assert safe_int("300", 0) == 300
    assert safe_int(150, 0) == 150
    assert safe_int("bad", 42) == 42
    assert safe_int(None, 7) == 7
