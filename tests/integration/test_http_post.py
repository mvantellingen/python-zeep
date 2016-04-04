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
        node = client.service.o1('EUR')
        assert node.text == 'Hoi'

        history = m.request_history[0]
        assert history.text == 'tickerSymbol=EUR'
