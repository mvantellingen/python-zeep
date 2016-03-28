import datetime

import freezegun

from zeep import cache


def test_cache():
    c = cache.SqliteCache(path=':memory:')
    c.add('http://tests.python-zeep.org/example.wsdl', b'content')

    result = c.get('http://tests.python-zeep.org/example.wsdl')
    assert result == b'content'


def test_cache_timeout():
    c = cache.SqliteCache(path=':memory:')
    c.add('http://tests.python-zeep.org/example.wsdl', b'content')
    result = c.get('http://tests.python-zeep.org/example.wsdl')
    assert result == b'content'

    freeze_dt = datetime.datetime.utcnow() + datetime.timedelta(seconds=7200)
    with freezegun.freeze_time(freeze_dt):
        result = c.get('http://tests.python-zeep.org/example.wsdl')
        assert result is None
