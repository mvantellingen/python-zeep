from lxml import etree
import requests


class Transport(object):
    def post(self, address, message, headers):
        print message
        response = requests.post(address, data=message, headers=headers)
        print response
        return response
