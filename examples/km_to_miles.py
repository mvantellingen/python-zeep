from __future__ import print_function
import zeep


client = zeep.Client(
    wsdl='http://www.webservicex.net/ConvertSpeed.asmx?WSDL')

client.wsdl.dump()

print (client.service.ConvertSpeed(100, 'kilometersPerhour', 'milesPerhour'))

http_get = client.bind('ConvertSpeeds', 'ConvertSpeedsHttpGet')
http_post = client.bind('ConvertSpeeds', 'ConvertSpeedsHttpPost')

print(http_get.ConvertSpeed(100, 'kilometersPerhour', 'milesPerhour'))
print(http_post.ConvertSpeed(100, 'kilometersPerhour', 'milesPerhour'))
