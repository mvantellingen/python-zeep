import pytest
import os
import requests_mock

import zeep

WSDL = os.path.join(os.path.dirname(__file__), 'test_http_post.wsdl')


@pytest.mark.requests
def test_get_urlreplacement():
    client = zeep.Client(WSDL)

    with requests_mock.mock() as m:
        m.get('http://example.com/o1/EUR/', text='<root>Hoi</root>')
        result = client.service.o1('EUR')
        assert result == 'Hoi'

        history = m.request_history[0]
        assert history._request.path_url == '/o1/EUR/'
