from zeep import Client
client=Client("file://test_recursive_error.wsdl")
client.wsdl.dump()