from collections import OrderedDict

from lxml import etree

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd
from zeep.wsdl import definitions, soap


def test_document_message_serializer():
    msg = soap.DocumentMessage(
        wsdl=None,
        name=None,
        operation=None,
        nsmap=soap.Soap11Binding.nsmap)

    namespace = 'http://docs.python-zeep.org/tests/document'

    # Fake resolve()
    msg.body = xsd.Element(
        etree.QName(namespace, 'response'),
        xsd.ComplexType([
            xsd.Element(etree.QName(namespace, 'arg1'), xsd.String()),
            xsd.Element(etree.QName(namespace, 'arg2'), xsd.String()),
        ])
    )
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    body, header, headerfault = msg.serialize(arg1='ah1', arg2='ah2')
    expected = """
        <?xml version="1.0"?>
        <soap-env:Body
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <ns0:response xmlns:ns0="http://docs.python-zeep.org/tests/document">
            <ns0:arg1>ah1</ns0:arg1>
            <ns0:arg2>ah2</ns0:arg2>
          </ns0:response>
        </soap-env:Body>
    """
    assert_nodes_equal(expected, body)


def test_document_message_deserializer():
    response_body = load_xml("""
        <SOAP-ENV:Body
            xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <mns:response xmlns:mns="http://docs.python-zeep.org/tests/document"
                SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <mns:return type="xsd:string">foobar</mns:return>
          </mns:response>
        </SOAP-ENV:Body>
    """)  # noqa

    msg = soap.DocumentMessage(
        wsdl=None,
        name=None,
        operation=None,
        nsmap=soap.Soap11Binding.nsmap)

    # Fake resolve()
    namespace = 'http://docs.python-zeep.org/tests/document'
    msg.abstract = definitions.AbstractMessage(
        etree.QName(namespace, 'Method1Response'))
    msg.abstract.parts = OrderedDict([
        ('body', definitions.MessagePart(
            element=xsd.Element(
                etree.QName(namespace, 'response'),
                xsd.ComplexType([
                    xsd.Element(etree.QName(namespace, 'return'), xsd.String()),
                ])
            ),
            type=None))
        ])

    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    result = msg.deserialize(response_body)
    assert result == 'foobar'


def test_rpc_message_serializer():
    msg = soap.RpcMessage(
        wsdl=None,
        name=None,
        operation=None,
        nsmap=soap.Soap11Binding.nsmap)

    # Fake resolve()
    msg.abstract = definitions.AbstractMessage(
        etree.QName('{http://docs.python-zeep.org/tests/rpc}Method1Response'))
    msg.abstract.parts = OrderedDict([
        ('arg1', definitions.MessagePart(
            element=None, type=xsd.String())),
        ('arg2', definitions.MessagePart(
            element=None, type=xsd.String())),

    ])
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }

    body, header, headerfault = msg.serialize(arg1='ah1', arg2='ah2')
    expected = """
        <?xml version="1.0"?>
        <soap-env:Body
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <ns0:Method1Response xmlns:ns0="http://docs.python-zeep.org/tests/rpc">
            <arg1>ah1</arg1>
            <arg2>ah2</arg2>
          </ns0:Method1Response>
        </soap-env:Body>
    """
    assert_nodes_equal(expected, body)


def test_rpc_message_deserializer():
    response_body = load_xml("""
        <SOAP-ENV:Body
            xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <mns:Method1Response xmlns:mns="http://docs.python-zeep.org/tests/rpc"
                SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <bstrReturn xsi:type="xsd:string">foobar</bstrReturn>
          </mns:Method1Response>
        </SOAP-ENV:Body>
    """)  # noqa

    msg = soap.RpcMessage(
        wsdl=None,
        name=None,
        operation=None,
        nsmap=soap.Soap11Binding.nsmap)

    # Fake resolve()
    msg.abstract = definitions.AbstractMessage(
        etree.QName('{http://docs.python-zeep.org/tests/rpc}Method1Response'))
    msg.abstract.parts = OrderedDict([
        ('bstrReturn', definitions.MessagePart(
            element=None, type=xsd.String()))
    ])
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }

    result = msg.deserialize(response_body)
    assert result == 'foobar'
