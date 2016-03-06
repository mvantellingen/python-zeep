from lxml import etree
import requests


class Transport(object):
    def post(self, address, message, headers):
        response = requests.post(address, data=message, headers=headers)
        return

        if response.status_code != 200:
            print response.content
            raise NotImplementedError("No error handling yet!")

        print etree.tostring(
            etree.fromstring(response.content), pretty_print=True)

        return response
