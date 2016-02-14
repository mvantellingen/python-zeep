from zeep import wsdl


def test_parse_wsdl():
    wisl = wsdl.WSDL('tests/wsdl_files/sample.wsdl')
