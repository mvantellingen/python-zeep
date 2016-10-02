import pytest
import requests_mock

from six import StringIO

from zeep import Client
from zeep.transports import Transport
 

@pytest.mark.requests
def test_xop(recwarn, monkeypatch):
    wsdl_main = StringIO("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/xsd-main"
          xmlns:sec="http://tests.python-zeep.org/wsdl-secondary"
          xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/xsd-main">
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-main"
                xmlns:tns="http://tests.python-zeep.org/xsd-main">
              <xsd:complexType name="responseTypeSimple">
                <xsd:sequence>
                  <xsd:element name="BinaryData" type="xsd:base64Binary"/>
                </xsd:sequence>
              </xsd:complexType>
              <xsd:complexType name="BinaryDataType">
                <xsd:simpleContent>
                  <xsd:extension base="xsd:base64Binary">
                    <xsd:anyAttribute namespace="##other" processContents="lax"/>
                  </xsd:extension>
                </xsd:simpleContent>
              </xsd:complexType>
              <xsd:complexType name="responseTypeComplex">
                <xsd:sequence>
                  <xsd:element name="BinaryData" type="tns:BinaryDataType"/>
                </xsd:sequence>
              </xsd:complexType>
              <xsd:element name="input" type="xsd:string"/>
              <xsd:element name="resultSimple" type="tns:responseTypeSimple"/>
              <xsd:element name="resultComplex" type="tns:responseTypeComplex"/>
            </xsd:schema>
          </wsdl:types>

          <wsdl:message name="dummyRequest">
            <wsdl:part name="response" element="tns:input"/>
          </wsdl:message>
          <wsdl:message name="dummyResponseSimple">
            <wsdl:part name="response" element="tns:resultSimple"/>
          </wsdl:message>
          <wsdl:message name="dummyResponseComplex">
            <wsdl:part name="response" element="tns:resultComplex"/>
          </wsdl:message>

          <wsdl:portType name="TestPortType">
            <wsdl:operation name="TestOperation1">
              <wsdl:input message="dummyRequest"/>
              <wsdl:output message="dummyResponseSimple"/>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <wsdl:input message="dummyRequest"/>
              <wsdl:output message="dummyResponseComplex"/>
            </wsdl:operation>
          </wsdl:portType>

          <wsdl:binding name="TestBinding" type="tns:TestPortType">
            <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
            <wsdl:operation name="TestOperation1">
              <soap:operation soapAction="urn:dummyRequest"/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
              <wsdl:output>
                <soap:body use="literal"/>
              </wsdl:output>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <soap:operation soapAction="urn:dummyRequest"/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
              <wsdl:output>
                <soap:body use="literal"/>
              </wsdl:output>
            </wsdl:operation>
          </wsdl:binding>
          <wsdl:service name="TestService">
            <wsdl:documentation>Test service</wsdl:documentation>
            <wsdl:port name="TestPortType" binding="tns:TestBinding">
              <soap:address location="http://tests.python-zeep.org/test"/>
            </wsdl:port>
          </wsdl:service>
        </wsdl:definitions>
    """.strip())

    client = Client(wsdl_main, transport=Transport())
    service = client.create_service("{http://tests.python-zeep.org/xsd-main}TestBinding", "http://tests.python-zeep.org/test")

    content_type = 'multipart/related; boundary="boundary"; type="application/xop+xml"; start="<soap:Envelope>"; start-info="application/soap+xml; charset=utf-8"'
    response1 = """\
--boundary
Content-Type: application/xop+xml; charset=utf-8; type="application/soap+xml"
Content-Transfer-Encoding: binary
Content-ID: <soap:Envelope>

<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xop="http://www.w3.org/2004/08/xop/include" xmlns:test="http://tests.python-zeep.org/xsd-main">
<soap:Body><test:resultSimple><test:BinaryData><xop:Include href="cid:id4"/></test:BinaryData></test:resultSimple></soap:Body></soap:Envelope>
--boundary
Content-Type: application/binary
Content-Transfer-Encoding: binary
Content-ID: <id4>

BINARYDATA
--boundary--"""
    response2 = """\
--boundary
Content-Type: application/xop+xml; charset=utf-8; type="application/soap+xml"
Content-Transfer-Encoding: binary
Content-ID: <soap:Envelope>

<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xop="http://www.w3.org/2004/08/xop/include" xmlns:test="http://tests.python-zeep.org/xsd-main">
<soap:Body><test:resultComplex><test:BinaryData><xop:Include href="cid:id4"/></test:BinaryData></test:resultComplex></soap:Body></soap:Envelope>
--boundary
Content-Type: application/binary
Content-Transfer-Encoding: binary
Content-ID: <id4>

BINARYDATA
--boundary--"""

    with requests_mock.mock() as m:
        m.post('http://tests.python-zeep.org/test', content=response2.encode("utf-8"), headers={"Content-Type": content_type})
        result = service.TestOperation2("")
        assert result["_value_1"] == "BINARYDATA".encode()
        m.post('http://tests.python-zeep.org/test', content=response1.encode("utf-8"), headers={"Content-Type": content_type})
        result = service.TestOperation1("")
        assert result == "BINARYDATA".encode()
