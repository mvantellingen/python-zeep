import pytest

pytest.register_assert_rewrite('tests.utils')


@pytest.fixture(autouse=True)
def no_requests(request, monkeypatch):
    if request.node.get_marker('requests'):
        return

    def func(*args, **kwargs):
        pytest.fail("External connections not allowed during tests.")

    monkeypatch.setattr("socket.socket", func)
