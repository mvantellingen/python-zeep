from __future__ import print_function
import zeep


client = zeep.Client(
    wsdl='http://www.webservicex.net/barcode.asmx?WSDL')
response = client.service.Code39('1234', 20, ShowCodeString=True, Title='ZEEP')
print(repr(response))
