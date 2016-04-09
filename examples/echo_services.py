from zeep.client import Client

# RPC style soap service
client = Client('http://www.soapclient.com/xml/soapresponder.wsdl')
print client.service.Method1('zeep', 'soap')
