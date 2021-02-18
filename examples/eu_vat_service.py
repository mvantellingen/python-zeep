from __future__ import print_function
import zeep


client = zeep.Client(
    wsdl='http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl')
print(client.service.checkVat('NL', '123456789B01'))
