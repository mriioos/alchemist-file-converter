from app.converters.base import BaseConverter, NoOptions
from app.registry import ConverterRegistry
from tests.conftest import MockConverter


def test_register_and_get():
    reg = ConverterRegistry()
    conv = MockConverter()
    reg.register(conv)

    assert reg.get("mock-to-out") is conv
    assert reg.get("nonexistent") is None


def test_all_returns_copy():
    reg = ConverterRegistry()
    conv = MockConverter()
    reg.register(conv)

    all_convs = reg.all()
    assert "mock-to-out" in all_convs
    assert len(all_convs) == 1


def test_duplicate_skipped():
    reg = ConverterRegistry()
    reg.register(MockConverter())
    reg.register(MockConverter())
    assert len(reg.all()) == 1


def test_discover_finds_real_converters():
    reg = ConverterRegistry()
    reg.discover()
    # Should find at least jpg-to-pdf and png-to-pdf
    assert "jpg-to-pdf" in reg.all()
    assert "png-to-pdf" in reg.all()
    assert len(reg.all()) >= 2
