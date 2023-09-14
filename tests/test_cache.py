import datetime
import time

import freezegun
import pytest

from zeep import cache


def test_base_add():
    base = cache.Base()
    with pytest.raises(NotImplementedError):
        base.add("test", b"test")


def test_base_get():
    base = cache.Base()
    with pytest.raises(NotImplementedError):
        base.get("test")


class TestSqliteCache:
    def test_in_memory(self):
        with pytest.raises(ValueError):
            cache.SqliteCache(path=":memory:")

    def test_cache(self, tmpdir):
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        c.add("http://tests.python-zeep.org/example.wsdl", b"content")

        result = c.get("http://tests.python-zeep.org/example.wsdl")
        assert result == b"content"

    def test_no_records(self, tmpdir):
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        result = c.get("http://tests.python-zeep.org/example.wsdl")
        assert result is None

    def test_has_expired(self, tmpdir):
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        c.add("http://tests.python-zeep.org/example.wsdl", b"content")

        freeze_dt = datetime.datetime.utcnow() + datetime.timedelta(seconds=7200)
        with freezegun.freeze_time(freeze_dt):
            result = c.get("http://tests.python-zeep.org/example.wsdl")
            assert result is None

    def test_has_not_expired(self, tmpdir):
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        c.add("http://tests.python-zeep.org/example.wsdl", b"content")
        result = c.get("http://tests.python-zeep.org/example.wsdl")
        assert result == b"content"


def test_memory_cache_timeout(tmpdir):
    c = cache.InMemoryCache()
    c.add("http://tests.python-zeep.org/example.wsdl", b"content")
    result = c.get("http://tests.python-zeep.org/example.wsdl")
    assert result == b"content"

    freeze_dt = datetime.datetime.utcnow() + datetime.timedelta(seconds=7200)
    with freezegun.freeze_time(freeze_dt):
        result = c.get("http://tests.python-zeep.org/example.wsdl")
        assert result is None


def test_memory_cache_share_data(tmpdir):
    a = cache.InMemoryCache()
    b = cache.InMemoryCache()
    a.add("http://tests.python-zeep.org/example.wsdl", b"content")

    result = b.get("http://tests.python-zeep.org/example.wsdl")
    assert result == b"content"


class TestIsExpired:
    def test_timeout_none(self):
        assert cache._is_expired(100, None) is False

    def test_has_expired(self):
        timeout = 7200
        utcnow = datetime.datetime.utcnow()
        value = utcnow + datetime.timedelta(seconds=timeout)
        with freezegun.freeze_time(utcnow):
            assert cache._is_expired(value, timeout) is False

    def test_has_not_expired(self):
        timeout = 7200
        utcnow = datetime.datetime.utcnow()
        value = utcnow - datetime.timedelta(seconds=timeout)
        with freezegun.freeze_time(utcnow):
            assert cache._is_expired(value, timeout) is False

def test_ttl_cache():
    c = cache.TTLCache(maxsize=5, ttl=10)
    c.add("http://tests.python-zeep.org/example.wsdl", b"content")

    result = c.get("http://tests.python-zeep.org/example.wsdl")
    assert result == b"content"
    cache._ttl_cache = None


def test_ttl_cache_no_records():
    c = cache.TTLCache(maxsize=5, ttl=10)
    result = c.get("http://tests.python-zeep.org/example.wsdl")
    assert result is None
    cache._ttl_cache = None


def test_ttl_cache_has_not_expired():
    c = cache.TTLCache(maxsize=5, ttl=10)
    c.add("http://tests.python-zeep.org/example.wsdl", b"content")
    freeze_dt = datetime.datetime.utcnow() + datetime.timedelta(seconds=2)
    with freezegun.freeze_time(freeze_dt):
        result = c.get("http://tests.python-zeep.org/example.wsdl")
        assert result == b"content"
        cache._ttl_cache = None


def test_ttl_cache_max_size_reached():
    max_size = 3
    c = cache.TTLCache(maxsize=max_size, ttl=2)
    for i in range(0, 5):
        c.add(f"http://tests.python-zeep.org/example{i}.wsdl", b"content")
    result = c.get("http://tests.python-zeep.org/example0.wsdl")
    assert result is None
    result = c.get("http://tests.python-zeep.org/example1.wsdl")
    assert result is None
    cache._ttl_cache = None


def test_ttl_cache_share_data():
    a = cache.TTLCache(maxsize=5, ttl=10)
    b = cache.TTLCache(maxsize=5, ttl=10)
    a.add("http://tests.python-zeep.org/example.wsdl", b"content")

    result = b.get("http://tests.python-zeep.org/example.wsdl")
    assert result == b"content"
    cache._ttl_cache = None


def test_ttl_cache_invalid_type():
    a = cache.TTLCache(maxsize=5, ttl=10)
    with pytest.raises(TypeError):
        a.add("http://tests.python-zeep.org/example.wsdl", 123456)
    cache._ttl_cache = None


def test_ttl_cache_has_expired():
    c = cache.TTLCache(maxsize=5, ttl=0.001)
    c.add("http://tests.python-zeep.org/example.wsdl", b"content")
    time.sleep(0.002) # Adding sleep because freezegun won't work here: https://github.com/spulec/freezegun/issues/477
    result = c.get("http://tests.python-zeep.org/example.wsdl")
    assert result is None
    cache._ttl_cache = None