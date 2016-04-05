import pytest


@pytest.fixture(autouse=True)
def no_requests(request, monkeypatch):
    if request.node.get_marker('requests'):
        return

    def func(session, method, url, *args, **kwargs):
        pytest.fail(
            "Session.request() not allowed during tests. (%s %s, %r, %r)" %
            (method, url, args, kwargs))

    monkeypatch.setattr("requests.sessions.Session.request", func)
