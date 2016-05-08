from pretend import stub

from zeep import __main__, client


def test_main_no_args(monkeypatch):
    def mock_init(self, *args, **kwargs):
        self.wsdl = stub(dump=lambda: None)

    monkeypatch.setattr(client.Client, '__init__', mock_init)
    args = __main__.parse_arguments(['foo.wsdl'])
    __main__.main(args)
