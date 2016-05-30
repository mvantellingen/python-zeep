from collections import OrderedDict

import pytest
from lxml import etree
from pretend import stub

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd
from zeep.wsdl import definitions, messages, soap


@pytest.fixture
def abstract_message_input():
    abstract = definitions.AbstractMessage(
        etree.QName('{http://test.python-zeep.org/tests/msg}Method'))
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
        etree.QName('{http://test.python-zeep.org/tests/msg}Response'))
    abstract.parts = OrderedDict([
        ('result', definitions.MessagePart(
            element=None, type=xsd.String())),
    ])
    return abstract


##
# DocumentMessage
#
def test_document_message_parse():
    xmlelement = load_xml("""
      <input
            xmlns="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
        <soap:body use="literal"/>
      </input>
    """)

    operation = stub()
    definitions_ = stub(
        target_namespace='',
        messages={},
        wsdl=stub())

    msg = messages.DocumentMessage.parse(
        definitions=definitions_,
        xmlelement=xmlelement,
        operation=operation,
        nsmap={})

    abstract_body = definitions.AbstractMessage(
        etree.QName('{http://test.python-zeep.org/tests/msg}Input'))
    abstract_body.parts['params'] = definitions.MessagePart(
        element=xsd.Element(etree.QName('input'), xsd.String()),
        type=None)

    msg.resolve(definitions_, abstract_body)

    assert msg.headerfault is None
    assert msg.header is None
    assert msg.body == abstract_body.parts['params'].element


def test_document_message_parse_with_header():
    xmlelement = load_xml("""
      <input
            xmlns="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:tns="http://tests.python-zeep.org/tns">
        <soap:header message="tns:Input" part="authentication" use="literal" />
        <soap:body use="literal"/>
      </input>
    """)

    operation = stub()
    definitions_ = stub(
        target_namespace='',
        messages={},
        wsdl=stub())

    msg = messages.DocumentMessage.parse(
        definitions=definitions_,
        xmlelement=xmlelement,
        operation=operation,
        nsmap={})

    abstract_message = definitions.AbstractMessage(
        etree.QName('{http://tests.python-zeep.org/tns}Input'))
    abstract_message.parts['params'] = definitions.MessagePart(
        element=xsd.Element(etree.QName('input'), xsd.String()),
        type=None)
    abstract_message.parts['authentication'] = definitions.MessagePart(
        element=xsd.Element(etree.QName('authentication'), xsd.String()),
        type=None)

    definitions_.messages[abstract_message.name.text] = abstract_message
    msg.resolve(definitions_, abstract_message)

    assert msg.headerfault is None
    assert msg.header == abstract_message.parts['authentication'].element
    assert msg.body == abstract_message.parts['params'].element
    assert len(abstract_message.parts.values()) == 2


def test_document_message_parse_with_header_other_message():
    xmlelement = load_xml("""
      <input
            xmlns="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:tns="http://tests.python-zeep.org/tns">
        <soap:header message="tns:InputHeader" part="authentication" use="literal" />
        <soap:body use="literal"/>
      </input>
    """)

    operation = stub()
    definitions_ = stub(
        target_namespace='',
        messages={},
        wsdl=stub())

    msg = messages.DocumentMessage.parse(
        definitions=definitions_,
        xmlelement=xmlelement,
        operation=operation,
        nsmap={})

    abstract_header = definitions.AbstractMessage(
        etree.QName('{http://tests.python-zeep.org/tns}InputHeader'))
    abstract_header.parts['authentication'] = definitions.MessagePart(
        element=xsd.Element(etree.QName('authentication'), xsd.String()),
        type=None)
    definitions_.messages[abstract_header.name.text] = abstract_header

    abstract_body = definitions.AbstractMessage(
        etree.QName('{http://test.python-zeep.org/tests/msg}Input'))
    abstract_body.parts['params'] = definitions.MessagePart(
        element=xsd.Element(etree.QName('input'), xsd.String()),
        type=None)

    msg.resolve(definitions_, abstract_body)

    assert msg.headerfault is None
    assert msg.header == abstract_header.parts['authentication'].element
    assert msg.body == abstract_body.parts['params'].element


def test_document_message_serializer():
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-actiGn')
    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    namespace = 'http://test.python-zeep.org/tests/document'

    # Fake resolve()
    msg.body = xsd.Element(
        etree.QName(namespace, 'response'),
        xsd.ComplexType([
            xsd.Element(etree.QName(namespace, 'arg1'), xsd.String()),
            xsd.Element(etree.QName(namespace, 'arg2'), xsd.String()),
        ])
    )
    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/document',
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
            <ns0:response xmlns:ns0="http://test.python-zeep.org/tests/document">
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:response>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_document_message_serializer_header():
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-actiGn')
    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    namespace = 'http://test.python-zeep.org/tests/document'

    # Fake resolve()
    msg.body = xsd.Element(
        etree.QName(namespace, 'response'),
        xsd.ComplexType([
            xsd.Element(etree.QName(namespace, 'arg1'), xsd.String()),
            xsd.Element(etree.QName(namespace, 'arg2'), xsd.String()),
        ])
    )
    msg.header = xsd.Element(
        etree.QName(namespace, 'auth'),
        xsd.ComplexType([
            xsd.Element(etree.QName(namespace, 'username'), xsd.String()),
        ])
    )
    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    serialized = msg.serialize(arg1='ah1', arg2='ah2', _soapheader={'username': 'mvantellingen'})
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <soap-env:Header>
            <ns0:auth xmlns:ns0="http://test.python-zeep.org/tests/document">
            <ns0:username>mvantellingen</ns0:username>
            </ns0:auth>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:response xmlns:ns0="http://test.python-zeep.org/tests/document">
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:response>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_document_message_serializer_header_custom_elm():
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-actiGn')
    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    namespace = 'http://test.python-zeep.org/tests/document'

    # Fake resolve()
    msg.body = xsd.Element(
        etree.QName(namespace, 'response'),
        xsd.ComplexType([
            xsd.Element(etree.QName(namespace, 'arg1'), xsd.String()),
            xsd.Element(etree.QName(namespace, 'arg2'), xsd.String()),
        ])
    )

    header = xsd.Element(
        '{http://test.python-zeep.org}auth',
        xsd.ComplexType([
            xsd.Element('{http://test.python-zeep.org}username', xsd.String()),
        ])
    )
    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    header_value = header(username='mvantellingen')
    serialized = msg.serialize(arg1='ah1', arg2='ah2', _soapheader=header_value)
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <soap-env:Header>
            <ns0:auth xmlns:ns0="http://test.python-zeep.org">
            <ns0:username>mvantellingen</ns0:username>
            </ns0:auth>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:response xmlns:ns0="http://test.python-zeep.org/tests/document">
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:response>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_document_message_serializer_header_custom_xml():
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-actiGn')
    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    namespace = 'http://test.python-zeep.org/tests/document'

    # Fake resolve()
    msg.body = xsd.Element(
        etree.QName(namespace, 'response'),
        xsd.ComplexType([
            xsd.Element(etree.QName(namespace, 'arg1'), xsd.String()),
            xsd.Element(etree.QName(namespace, 'arg2'), xsd.String()),
        ])
    )

    header_value = etree.Element('{http://test.python-zeep.org}auth')
    etree.SubElement(
        header_value, '{http://test.python-zeep.org}username'
    ).text = 'mvantellingen'

    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    serialized = msg.serialize(arg1='ah1', arg2='ah2', _soapheader=header_value)
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <soap-env:Header>
            <ns0:auth xmlns:ns0="http://test.python-zeep.org">
            <ns0:username>mvantellingen</ns0:username>
            </ns0:auth>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:response xmlns:ns0="http://test.python-zeep.org/tests/document">
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
          <mns:response xmlns:mns="http://test.python-zeep.org/tests/document"
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
    namespace = 'http://test.python-zeep.org/tests/document'
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
        'body': 'http://test.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    result = msg.deserialize(response_body)
    assert result == 'foobar'


##
# RPC Message
def test_rpc_message_parse():
    xmlelement = load_xml("""
      <input
            xmlns="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
        <soap:body use="encoded" namespace="http://tests.python-zeep.org/rpc"
                   encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"/>
      </input>
    """)

    operation = stub()
    definitions_ = stub(
        target_namespace='',
        messages={},
        wsdl=stub())

    msg = messages.RpcMessage.parse(
        definitions=definitions_,
        xmlelement=xmlelement,
        operation=operation,
        nsmap={})

    abstract_body = definitions.AbstractMessage(
        etree.QName('{http://test.python-zeep.org/tests/msg}Input'))
    abstract_body.parts['arg1'] = definitions.MessagePart(
        element=None, type=xsd.String())
    abstract_body.parts['arg2'] = definitions.MessagePart(
        element=None, type=xsd.String())

    msg.resolve(definitions_, abstract_body)

    assert msg.headerfault is None
    assert msg.header is None
    assert msg.body is not None


def test_rpc_message_serializer(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.RpcMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    msg._info = {
        'body': {
            'namespace': 'http://test.python-zeep.org/tests/rpc',
        },
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <soap-env:Body>
            <ns0:Method xmlns:ns0="http://test.python-zeep.org/tests/rpc">
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
          <mns:Response xmlns:mns="http://test.python-zeep.org/tests/rpc"
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

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_output)

    result = msg.deserialize(response_body)
    assert result == 'foobar'


def test_rpc_message_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.RpcMessage(
        wsdl=wsdl, name=None, operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'


def test_rpc_message_signature_output(abstract_message_output):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(soapaction='my-action')

    msg = messages.RpcMessage(
        wsdl=wsdl, name=None, operation=operation,
        nsmap=soap.Soap11Binding.nsmap)

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_output)
    assert msg.signature(True) == 'xsd:string'


##
# URLEncoded Message
#
def test_urlencoded_serialize(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action', name='foo')

    msg = messages.UrlEncoded(
        wsdl=wsdl, name=None, operation=operation)

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    assert serialized.headers == {'Content-Type': 'text/xml; charset=utf-8'}
    assert serialized.path == 'my-action'
    assert serialized.content == {'arg1': 'ah1', 'arg2': 'ah2'}


def test_urlencoded_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action', name='foo')

    msg = messages.UrlEncoded(
        wsdl=wsdl, name=None, operation=operation)

    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'


##
# URLReplacement Message
#
def test_urlreplacement_serialize(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action/(arg1)/(arg2)/', name='foo')

    msg = messages.UrlReplacement(
        wsdl=wsdl, name=None, operation=operation)

    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/rpc',
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    assert serialized.headers == {'Content-Type': 'text/xml; charset=utf-8'}
    assert serialized.path == 'my-action/ah1/ah2/'
    assert serialized.content == ''


def test_urlreplacement_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action/(arg1)/(arg2)/', name='foo')

    msg = messages.UrlReplacement(
        wsdl=wsdl, name=None, operation=operation)

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'


##
# MimeContent Message
#
def test_mime_content_serialize_form_urlencoded(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action', name='foo')

    msg = messages.MimeContent(
        wsdl=wsdl, name=None, operation=operation,
        content_type='application/x-www-form-urlencoded',
        part_name='')

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)

    serialized = msg.serialize(arg1='ah1', arg2='ah2')
    assert serialized.headers == {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    assert serialized.path == 'my-action'
    assert serialized.content == 'arg1=ah1&arg2=ah2'


def test_mime_content_serialize_xml():
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action', name='foo')

    element_1 = xsd.Element('arg1', xsd.ComplexType([
        xsd.Element('arg1_1', xsd.String())
    ]))
    element_2 = xsd.Element('arg2', xsd.String())
    abstract_message = definitions.AbstractMessage(
        etree.QName('{http://test.python-zeep.org/tests/msg}Method'))
    abstract_message.parts = OrderedDict([
        ('xarg1', definitions.MessagePart(element=element_1, type=None)),
        ('xarg2', definitions.MessagePart(element=element_2, type=None)),
    ])

    msg = messages.MimeContent(
        wsdl=wsdl, name=None, operation=operation, content_type='text/xml',
        part_name=None)

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message)

    serialized = msg.serialize(xarg1={'arg1_1': 'uh'}, xarg2='bla')
    assert serialized.headers == {
        'Content-Type': 'text/xml'
    }
    assert serialized.path == 'my-action'
    assert_nodes_equal(
        load_xml(serialized.content),
        load_xml(
            "<foo><xarg1><arg1_1>uh</arg1_1></xarg1><xarg2>bla</xarg2></foo>"))


def test_mime_content_signature(abstract_message_input):
    wsdl = stub(schema=stub(_prefix_map={}))
    operation = stub(location='my-action', name='foo')

    msg = messages.MimeContent(
        wsdl=wsdl, name=None, operation=operation,
        content_type='application/x-www-form-urlencoded',
        part_name='')

    msg._info = {
        'body': {'namespace': 'http://test.python-zeep.org/tests/rpc'},
        'header': None,
        'headerfault': None
    }
    msg.resolve(wsdl, abstract_message_input)
    assert msg.signature() == 'arg1: xsd:string, arg2: xsd:string'


def test_mime_multipart_parse():
    load_xml("""
        <output
            xmlns="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:mime="http://schemas.xmlsoap.org/wsdl/mime/">
          <mime:multipartRelated>
              <mime:part>
                  <soap:body parts="body" use="literal"/>
              </mime:part>
              <mime:part>
                  <mime:content part="test" type="text/html"/>
              </mime:part>
              <mime:part>
                  <mime:content part="logo" type="image/gif"/>
                  <mime:content part="logo" type="image/jpeg"/>
              </mime:part>
          </mime:multipartRelated>
       </output>
    """)
