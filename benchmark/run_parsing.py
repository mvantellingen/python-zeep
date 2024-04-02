import time
import cProfile
import pretend  # pip install pretend

from lxml import etree
from lxml.builder import ElementMaker

from zeep import Client


def build_xml(num):
    soap = ElementMaker(namespace="http://schemas.xmlsoap.org/soap/envelope/")
    tns = ElementMaker(namespace="http://benchmark.python-zeep.org/")

    body = soap.Body()
    envelope = soap.Envelope(body)

    items = tns.items()
    body.append(items)

    for i in range(num):
        item = tns.item(
            tns.id(str(i)),
            tns.name("SomeName"),
            tns.active("true"),
            tns.price("1234.12"),
        )
        items.append(item)
    return etree.tostring(envelope, pretty_print=True)


def main(enable_profile=False, items=100):
    print("Preparing data (%d items)" % items)
    client = Client("benchmark.wsdl")
    data = build_xml(items)

    response = pretend.stub(status_code=200, headers={}, content=data)

    operation = client.service._binding._operations["GetItemList"]

    print("Parsing data")

    if enable_profile:
        profile = cProfile.Profile()
        profile.enable()

    # Run code
    st = time.time()
    result = run(client, operation, response)
    et = time.time()
    print("Run took %.2fms" % ((et - st) * 1000))

    if enable_profile:
        profile.disable()
        profile.dump_stats("benchmark.prof")

    assert result


def run(client, operation, response):
    return client.service._binding.process_reply(client, operation, response)


if __name__ == "__main__":
    main(enable_profile=False, items=10000)
