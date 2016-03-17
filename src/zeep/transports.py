from lxml import etree
import requests


class Transport(object):

    def load(self, url):
        response = requests.get(url)
        return response.content

    def post(self, address, message, headers):
        response = requests.post(address, data=message, headers=headers)
        return response
