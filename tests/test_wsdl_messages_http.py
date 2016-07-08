from collections import OrderedDict

import pytest
from lxml import etree
from pretend import stub

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd
from zeep.wsdl import definitions, messages


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
