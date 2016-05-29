from lxml import etree
import pytest

from zeep.wsdl import soap
from tests.utils import load_xml


def test_soap11_process_error():
    response = load_xml("""
        <soapenv:Envelope
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:stoc="http://example.com/stockquote.xsd">
          <soapenv:Body>
            <soapenv:Fault>
              <faultcode>fault-code</faultcode>
              <faultstring>fault-string</faultstring>
              <detail>
                <e:myFaultDetails xmlns:e="http://myexample.org/faults">
                  <e:message>detail-message</e:message>
                  <e:errorcode>detail-code</e:errorcode>
                </e:myFaultDetails>
              </detail>
            </soapenv:Fault>
          </soapenv:Body>
        </soapenv:Envelope>
    """)
    binding = soap.Soap11Binding(
        wsdl=None, name=None, port_name=None, transport=None,
        default_style=None)

    try:
        binding.process_error(response)
        assert False
    except soap.Fault as exc:
        assert exc.message == 'fault-string'
        assert exc.code == 'fault-code'
        assert exc.actor is None
        assert 'detail-message' in etree.tostring(exc.detail).decode('utf-8')


def test_soap12_process_error():
    response = load_xml("""
        <soapenv:Envelope
            xmlns:soapenv="http://www.w3.org/2003/05/soap-envelope">
          <soapenv:Body>
            <soapenv:Fault>
             <soapenv:Code>
               <soapenv:Value>fault-code</soapenv:Value>
               <soapenv:Subcode>
                <soapenv:Value>fault-subcode</soapenv:Value>
               </soapenv:Subcode>
             </soapenv:Code>
             <soapenv:Reason>
              <soapenv:Text xml:lang="en-US">us-error</soapenv:Text>
              <soapenv:Text xml:lang="nl-NL">nl-error</soapenv:Text>
             </soapenv:Reason>
             <soapenv:Detail>
              <e:myFaultDetails
                xmlns:e="http://myexample.org/faults" >
                <e:message>Invalid credit card details</e:message>
                <e:errorcode>999</e:errorcode>
              </e:myFaultDetails>
             </soapenv:Detail>
           </soapenv:Fault>
         </soapenv:Body>
        </soapenv:Envelope>
    """)
    binding = soap.Soap12Binding(
        wsdl=None, name=None, port_name=None, transport=None,
        default_style=None)

    try:
        binding.process_error(response)
        assert False
    except soap.Fault as exc:
        assert exc.message == 'us-error'
        assert exc.code == 'fault-code'
