from lxml import etree

from tests.utils import load_xml
from zeep.exceptions import Fault
from zeep.wsdl import bindings


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
    binding = bindings.Soap11Binding(
        wsdl=None, name=None, port_name=None, transport=None,
        default_style=None)

    try:
        binding.process_error(response, None)
        assert False
    except Fault as exc:
        assert exc.message == 'fault-string'
        assert exc.code == 'fault-code'
        assert exc.actor is None
        assert exc.subcodes is None
        assert 'detail-message' in etree.tostring(exc.detail).decode('utf-8')


def test_soap12_process_error():
    response = """
        <soapenv:Envelope
            xmlns="http://example.com/example1"
            xmlns:ex="http://example.com/example2"
            xmlns:soapenv="http://www.w3.org/2003/05/soap-envelope">
          <soapenv:Body>
            <soapenv:Fault>
             <soapenv:Code>
               <soapenv:Value>fault-code</soapenv:Value>
               %s
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
    """
    subcode = """
               <soapenv:Subcode>
                 <soapenv:Value>%s</soapenv:Value>
                 %s
               </soapenv:Subcode>
    """
    binding = bindings.Soap12Binding(
        wsdl=None, name=None, port_name=None, transport=None,
        default_style=None)

    try:
        binding.process_error(load_xml(response % ""), None)
        assert False
    except Fault as exc:
        assert exc.message == 'us-error'
        assert exc.code == 'fault-code'
        assert exc.subcodes == []

    try:
        binding.process_error(
            load_xml(response % subcode % ("fault-subcode1", "")), None)
        assert False
    except Fault as exc:
        assert exc.message == 'us-error'
        assert exc.code == 'fault-code'
        assert len(exc.subcodes) == 1
        assert exc.subcodes[0].namespace == 'http://example.com/example1'
        assert exc.subcodes[0].localname == 'fault-subcode1'

    try:
        binding.process_error(
            load_xml(response % subcode % ("fault-subcode1", subcode % ("ex:fault-subcode2", ""))),
            None)
        assert False
    except Fault as exc:
        assert exc.message == 'us-error'
        assert exc.code == 'fault-code'
        assert len(exc.subcodes) == 2
        assert exc.subcodes[0].namespace == 'http://example.com/example1'
        assert exc.subcodes[0].localname == 'fault-subcode1'
        assert exc.subcodes[1].namespace == 'http://example.com/example2'
        assert exc.subcodes[1].localname == 'fault-subcode2'
