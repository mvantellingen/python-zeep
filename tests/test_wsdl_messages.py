import pytest
from collections import OrderedDict

from lxml import etree
from pretend import stub

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd
from zeep.wsdl import definitions, messages, soap


@pytest.fixture
def abstract_message_input():
    abstract = definitions.AbstractMessage(
        etree.QName('{http://docs.python-zeep.org/tests/msg}Method'))
    abstract.parts = OrderedDict([
        ('arg1', definitions.MessagePart(
            element=None, type=xsd.String())),
        ('arg2', definitions.MessagePart(
            element=None, type=xsd.String())),
    ])
    return abstract


@pytest.fixture
def abstract_message_output():
    abstract = definitions.AbstractMessage(
        etree.QName('{http://docs.python-zeep.org/tests/msg}Response'))
    abstract.parts = OrderedDict([
        ('result', definitions.MessagePart(
            element=None, type=xsd.String())),
    ])
    return abstract


def test_document_message_serializer():
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-actiGn')
    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
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

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <soap-env:Body>
            <ns0:response xmlns:ns0="http://docs.python-zeep.org/tests/document">
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:response>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


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
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
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


def test_rpc_message_serializer(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.RpcMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <soap-env:Body>
            <ns0:Method xmlns:ns0="http://docs.python-zeep.org/tests/rpc">
              <arg1>ah1</arg1>
              <arg2>ah2</arg2>
            </ns0:Method>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_rpc_message_deserializer(abstract_message_output):
    response_body = load_xml("""
        <SOAP-ENV:Body
            xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <mns:Response xmlns:mns="http://docs.python-zeep.org/tests/rpc"
                SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <result xsi:type="xsd:string">foobar</result>
          </mns:Response>
        </SOAP-ENV:Body>
    """)  # noqa
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.RpcMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    # Fake resolve()
    msg.abstract = abstract_message_output
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }

    result = msg.deserialize(response_body)
    assert result == 'foobar'


def test_rpc_message_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.RpcMessage(
        wsdl=wsdl, name=None, operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'


def test_rpc_message_signature_output(abstract_message_output):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.RpcMessage(
        wsdl=wsdl, name=None, operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    # Fake resolve()
    msg.abstract = abstract_message_output
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }
    assert msg.signature(True) == 'result: xsd:string'


def test_urlencoded_serialize(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action')

    msg = messages.UrlEncoded(
        wsdl=wsdl, name=None, operation=operation)

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    assert serialized.headers == {'Content-Type': 'text/xml; charset=utf-8'}
    assert serialized.path == 'my-action'
    assert serialized.content == {'arg1': 'ah1', 'arg2': 'ah2'}


def test_urlencoded_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action')

    msg = messages.UrlEncoded(
        wsdl=wsdl, name=None, operation=operation)

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'


def test_urlreplacement_serialize(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action/(arg1)/(arg2)/')

    msg = messages.UrlReplacement(
        wsdl=wsdl, name=None, operation=operation)

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    assert serialized.headers == {'Content-Type': 'text/xml; charset=utf-8'}
    assert serialized.path == 'my-action/ah1/ah2/'
    assert serialized.content == ''


def test_urlreplacement_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action/(arg1)/(arg2)/')

    msg = messages.UrlReplacement(
        wsdl=wsdl, name=None, operation=operation)

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'


def test_mime_content_serialize_form_urlencoded(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action')

    msg = messages.MimeContent(
        wsdl=wsdl, name=None, operation=operation,
        content_type='application/x-www-form-urlencoded')

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    assert serialized.headers == {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    assert serialized.path == 'my-action'
    assert serialized.content == 'arg1=ah1&arg2=ah2'


def test_mime_content_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action')

    msg = messages.MimeContent(
        wsdl=wsdl, name=None, operation=operation,
        content_type='application/x-www-form-urlencoded')

    # Fake resolve()
    msg.abstract = abstract_message_input
    msg.namespace = {
        'body': 'http://docs.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'
