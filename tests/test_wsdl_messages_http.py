from collections import OrderedDict

import pytest
from lxml import etree
from pretend import stub
from six import StringIO

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd
from zeep.wsdl import definitions, messages, wsdl


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


##
# URLEncoded Message
#
def test_urlencoded_serialize(abstract_message_input):
    wsdl = stub(types=stub(_prefix_map={}))
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
    wsdl = stub(types=stub(_prefix_map={}))
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
    wsdl = stub(types=stub(_prefix_map={}))
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
    wsdl = stub(types=stub(_prefix_map={}))
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
    wsdl = stub(types=stub(_prefix_map={}))
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
    wsdl = stub(types=stub(_prefix_map={}))
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
    wsdl = stub(types=stub(_prefix_map={}))
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


def test_mime_content_serialize():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:http="http://schemas.xmlsoap.org/wsdl/http/"
                 xmlns:mime="http://schemas.xmlsoap.org/wsdl/mime/"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">

      <message name="Input">
        <part name="arg1" type="xsd:string"/>
        <part name="arg2" type="xsd:string"/>
      </message>
      <message name="Output">
        <part name="Body" type="xsd:string"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
          <output message="Output"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <http:binding verb="POST"/>
        <operation name="TestOperation">
          <http:operation location="/test-operation"/>
          <input>
            <mime:content type="application/x-www-form-urlencoded"/>
          </input>
          <output>
            <mime:mimeXml part="Body"/>
          </output>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    assert operation.input.signature() == 'arg1: xsd:string, arg2: xsd:string'

    serialized = operation.input.serialize(arg1='ah1', arg2='ah2')
    assert serialized.content == 'arg1=ah1&arg2=ah2'


def test_mime_xml_deserialize():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:http="http://schemas.xmlsoap.org/wsdl/http/"
                 xmlns:mime="http://schemas.xmlsoap.org/wsdl/mime/"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/tns"
            targetNamespace="http://tests.python-zeep.org/tns"
                elementFormDefault="qualified">
          <xsd:element name="response">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="item_1" type="xsd:string"/>
                <xsd:element name="item_2" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
      </types>

      <message name="Input">
        <part name="arg1" type="xsd:string"/>
        <part name="arg2" type="xsd:string"/>
      </message>
      <message name="Output">
        <part name="Body" element="tns:response"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
          <output message="Output"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <http:binding verb="POST"/>
        <operation name="TestOperation">
          <http:operation location="/test-operation"/>
          <input>
            <mime:content type="application/x-www-form-urlencoded"/>
          </input>
          <output>
            <mime:mimeXml part="Body"/>
          </output>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    assert operation.input.signature() == 'arg1: xsd:string, arg2: xsd:string'

    node = """
        <response xmlns="http://tests.python-zeep.org/tns">
          <item_1>foo</item_1>
          <item_2>bar</item_2>
        </response>
    """.strip()

    serialized = operation.output.deserialize(node)
    assert serialized.item_1 == 'foo'
    assert serialized.item_2 == 'bar'


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
