import datetime

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

    @pytest.mark.network
    def test_has_expired(self, tmpdir):
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        c.add("http://tests.python-zeep.org/example.wsdl", b"content")

        freeze_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=7200
        )
        with freezegun.freeze_time(freeze_dt):
            result = c.get("http://tests.python-zeep.org/example.wsdl")
            assert result is None

    def test_has_not_expired(self, tmpdir):
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        c.add("http://tests.python-zeep.org/example.wsdl", b"content")
        result = c.get("http://tests.python-zeep.org/example.wsdl")
        assert result == b"content"

    def test_cache_on_whole_second(self, tmpdir):
        # isoformat() leaves out the microseconds when they're zero, which the
        # old sqlite3 timestamp converter couldn't parse.
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        frozen = datetime.datetime(2026, 11, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
        with freezegun.freeze_time(frozen):
            c.add("http://tests.python-zeep.org/example.wsdl", b"content")
            result = c.get("http://tests.python-zeep.org/example.wsdl")
        assert result == b"content"

    @pytest.mark.parametrize(
        "created",
        [
            "2026-11-15 09:00:00.123456+00:00",
            "2026-11-15 09:00:00+00:00",
            "2026-11-15 09:00:00.123456",
        ],
    )
    def test_reads_existing_rows(self, tmpdir, created):
        # Rows written by older zeep versions through the default sqlite3
        # adapter, with and without a UTC offset.
        path = tmpdir.join("sqlite.cache.db").strpath
        c = cache.SqliteCache(path=path, timeout=None)
        with c.db_connection() as conn:
            conn.execute(
                "INSERT INTO request (created, url, content) VALUES (?, ?, ?)",
                (
                    created,
                    "http://tests.python-zeep.org/example.wsdl",
                    c._encode_data(b"content"),
                ),
            )
            conn.commit()
        assert c.get("http://tests.python-zeep.org/example.wsdl") == b"content"

    def test_no_sqlite3_datetime_deprecation(self, tmpdir, recwarn):
        c = cache.SqliteCache(path=tmpdir.join("sqlite.cache.db").strpath)
        c.add("http://tests.python-zeep.org/example.wsdl", b"content")
        assert c.get("http://tests.python-zeep.org/example.wsdl") == b"content"
        assert not [w for w in recwarn if issubclass(w.category, DeprecationWarning)]


@pytest.mark.network
def test_memory_cache_timeout(tmpdir):
    c = cache.InMemoryCache()
    c.add("http://tests.python-zeep.org/example.wsdl", b"content")
    result = c.get("http://tests.python-zeep.org/example.wsdl")
    assert result == b"content"

    freeze_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=7200
    )
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

    @pytest.mark.network
    def test_has_expired(self):
        timeout = 7200
        utcnow = datetime.datetime.now(datetime.timezone.utc)
        value = utcnow + datetime.timedelta(seconds=timeout)
        with freezegun.freeze_time(utcnow):
            assert cache._is_expired(value, timeout) is False

    @pytest.mark.network
    def test_has_not_expired(self):
        timeout = 7200
        utcnow = datetime.datetime.now(datetime.timezone.utc)
        value = utcnow - datetime.timedelta(seconds=timeout)
        with freezegun.freeze_time(utcnow):
            assert cache._is_expired(value, timeout) is False
