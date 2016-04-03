from __future__ import print_function
import zeep


client = zeep.Client(
    wsdl='http://www.webservicex.net/ConvertSpeed.asmx?WSDL')
print (client.service.ConvertSpeed(100, 'kilometersPerhour', 'milesPerhour'))
