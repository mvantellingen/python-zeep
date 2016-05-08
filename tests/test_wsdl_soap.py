from collections import OrderedDict

from lxml import etree

from tests.utils import load_xml
from zeep.wsdl import definitions, soap
from zeep.xsd import builtins


def test_rpc_message_deserializer():
    response_body = load_xml("""
        <SOAP-ENV:Body
            xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:tns="http://www.SoapClient.com/xml/SoapResponder.wsdl"
            xmlns:xsd1="http://www.SoapClient.com/xml/SoapResponder.xsd"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/">
          <mns:Method1Response xmlns:mns="http://www.SoapClient.com/xml/SoapResponder.xsd"
                SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <bstrReturn xsi:type="xsd:string">
                Your input parameters are zeep and soap
            </bstrReturn>
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
        etree.QName(
            'http://www.SoapClient.com/xml/SoapResponder.wsdl',
            'Method1Response'
        ))
    msg.abstract.parts = OrderedDict([
        ('bstrReturn', definitions.MessagePart(
            element=None, type=builtins.String()))
    ])
    msg.namespace = {
        'body': 'http://www.SoapClient.com/xml/SoapResponder.xsd',
        'header': None,
        'headerfault': None
    }

    msg.deserialize(response_body)
